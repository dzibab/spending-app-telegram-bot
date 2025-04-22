"""Handler for importing spending data from CSV files."""

import csv
import io

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from db import db
from handlers.common import cancel, handle_db_error, log_user_action
from utils.date_utils import parse_date
from utils.logging import logger

# Define states for the conversation
UPLOAD_FILE, CONFIRM_IMPORT = range(2)


async def start_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for /import command to start the import conversation."""
    user_id = update.effective_user.id
    log_user_action(user_id, "initiated importing spendings from CSV")

    # If triggered from settings menu via callback query, store the original message ID
    if hasattr(update, "callback_query") and update.callback_query:
        if not context.user_data.get("import_from_settings"):
            context.user_data["import_from_settings"] = True

    # Show import instructions with template download option
    keyboard = [[InlineKeyboardButton("📝 Download Template", callback_data="import_template")]]

    if context.user_data.get("import_from_settings"):
        keyboard.append([InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📥 *Import Your Spending Data*\n\n"
        "To import your spendings, please upload a CSV file with the following columns:\n\n"
        "- *Date*: Required (formats: YYYY-MM-DD, DD-MM-YYYY with delimiters -, / or .)\n"
        "- *Amount*: Required (numeric value)\n"
        "- *Currency*: Required (3-letter currency code)\n"
        "- *Category*: Required\n"
        "- *Description*: Optional\n\n"
        "You can download a template file to get started or simply upload your own CSV file.",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return UPLOAD_FILE


async def send_import_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a CSV template file to the user."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    log_user_action(user_id, "requested import template")

    # Create CSV template in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    headers = ["Date", "Amount", "Currency", "Category", "Description"]
    writer.writerow(headers)

    # Write some sample rows
    writer.writerow(["2025-04-18", "12.50", "USD", "Food", "Lunch"])
    writer.writerow(["2025-04-17", "35.00", "USD", "Transport", "Taxi"])
    writer.writerow(["2025-04-15", "150.00", "USD", "Shopping", "New shoes"])

    # Prepare file for sending
    output.seek(0)

    # Send template file
    await query.message.reply_document(
        document=output.getvalue().encode(),
        filename="spending_import_template.csv",
        caption="Here's a template CSV file for importing your spendings. Fill it with your own data and upload.",
    )

    # Show further instructions
    keyboard = []
    if context.user_data.get("import_from_settings"):
        keyboard.append([InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")])

    if keyboard:
        await query.message.reply_text(
            "Please upload your CSV file when ready.", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.message.reply_text("Please upload your CSV file when ready.")

    return UPLOAD_FILE


async def handle_import_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation from import and return to settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    log_user_action(user_id, "cancelled import from settings")

    # Clear import-related data
    if "import_from_settings" in context.user_data:
        del context.user_data["import_from_settings"]

    # Return to data management menu in settings
    keyboard = [
        [InlineKeyboardButton("📤 Export Spendings", callback_data="settings_action:export")],
        [InlineKeyboardButton("📥 Import Spendings", callback_data="settings_action:import")],
        [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
    ]

    await query.edit_message_text(
        "📊 *Data Management*\n\nImport or export your spending data:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

    return ConversationHandler.END


async def handle_csv_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle CSV file uploads from any context."""
    if not update.message or not update.message.document:
        return

    # Only process CSV files
    file_name = update.message.document.file_name.lower()
    if not file_name.endswith(".csv"):
        return

    # Process the file
    user_id = update.effective_user.id
    log_user_action(user_id, "uploaded a CSV file for import (direct handler)")

    await update.message.reply_text("📊 Analyzing your CSV file. This may take a moment...")

    try:
        # Get the file from Telegram
        file = await context.bot.get_file(update.message.document.file_id)
        bytes_content = await file.download_as_bytearray()
        csv_content = io.StringIO(bytes_content.decode("utf-8"))

        # Analyze the CSV file without importing
        stats, valid_spendings = await analyze_csv_import(user_id, csv_content)

        # Check if there are validation errors with headers
        if stats["errors"] and "header" in stats["errors"][0].lower():
            error_message = stats["errors"][0]
            keyboard = [
                [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
                [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]
                if context.user_data.get("import_from_settings")
                else [],
            ]
            await update.message.reply_text(
                f"❌ {error_message}",
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            )
            return

        # Generate summary message
        if stats["success"] > 0:
            # Store the analyzed data for later import
            context.user_data["csv_import_data"] = {
                "stats": stats,
                "valid_spendings": valid_spendings,
            }

            # Create confirmation message
            message = f"📋 Import Summary:\n\n"
            message += f"• {stats['success']} spendings will be imported\n"

            if stats["failed"] > 0:
                message += f"• {stats['failed']} invalid entries will be skipped\n"

            if stats["new_categories"]:
                message += f"• {len(stats['new_categories'])} new categories will be added: {', '.join(stats['new_categories'])}\n"

            if stats["new_currencies"]:
                message += f"• {len(stats['new_currencies'])} new currencies will be added: {', '.join(stats['new_currencies'])}\n"

            if stats["errors"]:
                message += f"\nThere are some validation issues. First 3 errors (of {len(stats['errors'])} total):\n"
                message += "\n".join(stats["errors"][:3])

            message += "\n\nWould you like to proceed with the import?"

            # Create confirmation buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Import", callback_data="import_confirm:proceed"),
                    InlineKeyboardButton("❌ No, Cancel", callback_data="import_confirm:cancel"),
                ]
            ]

            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

        else:
            # No valid entries found
            error_message = "❌ No valid spending entries found in the CSV file."
            if stats["errors"]:
                error_message += f"\n\nFirst 3 errors (of {len(stats['errors'])} total):\n"
                error_message += "\n".join(stats["errors"][:3])

            keyboard = [
                [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
                [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]
                if context.user_data.get("import_from_settings")
                else [],
            ]

            await update.message.reply_text(
                error_message, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )

    except Exception as e:
        error_message = (
            f"❌ Error processing file: {e!s}\n\nPlease check your file format and try again."
        )
        logger.error(f"Error processing CSV file: {e}")

        keyboard = [
            [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
            [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]
            if context.user_data.get("import_from_settings")
            else [],
        ]

        await update.message.reply_text(
            error_message, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

        await handle_db_error(update, "analyzing spendings", e)


async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the uploaded CSV file within conversation context."""
    user_id = update.effective_user.id
    log_user_action(user_id, "uploaded a file for import (conversation handler)")

    # Check if a file was provided
    if not update.message.document:
        await update.message.reply_text(
            "Please upload a CSV file. Use /cancel to abort.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]]
            )
            if context.user_data.get("import_from_settings")
            else None,
        )
        return UPLOAD_FILE

    # Check if the file is a CSV
    if not update.message.document.file_name.lower().endswith(".csv"):
        await update.message.reply_text(
            "Please upload a CSV file, not another file type.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]]
            )
            if context.user_data.get("import_from_settings")
            else None,
        )
        return UPLOAD_FILE

    await update.message.reply_text("📊 Analyzing your file. This may take a moment...")

    try:
        # Get the file from Telegram
        file = await context.bot.get_file(update.message.document.file_id)
        bytes_content = await file.download_as_bytearray()
        csv_content = io.StringIO(bytes_content.decode("utf-8"))

        # Analyze the CSV file without importing
        stats, valid_spendings = await analyze_csv_import(user_id, csv_content)

        # Check if there are validation errors with headers
        if stats["errors"] and "header" in stats["errors"][0].lower():
            error_message = stats["errors"][0]
            keyboard = [
                [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
                [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]
                if context.user_data.get("import_from_settings")
                else [],
            ]
            await update.message.reply_text(
                f"❌ {error_message}",
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            )
            return UPLOAD_FILE

        # Generate summary message
        if stats["success"] > 0:
            # Store the analyzed data for later import
            context.user_data["csv_import_data"] = {
                "stats": stats,
                "valid_spendings": valid_spendings,
            }

            # Create confirmation message
            message = f"📋 Import Summary:\n\n"
            message += f"• {stats['success']} spendings will be imported\n"

            if stats["failed"] > 0:
                message += f"• {stats['failed']} invalid entries will be skipped\n"

            if stats["new_categories"]:
                message += f"• {len(stats['new_categories'])} new categories will be added: {', '.join(stats['new_categories'])}\n"

            if stats["new_currencies"]:
                message += f"• {len(stats['new_currencies'])} new currencies will be added: {', '.join(stats['new_currencies'])}\n"

            if stats["errors"]:
                message += f"\nThere are some validation issues. First 3 errors (of {len(stats['errors'])} total):\n"
                message += "\n".join(stats["errors"][:3])

            message += "\n\nWould you like to proceed with the import?"

            # Create confirmation buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Import", callback_data="import_confirm:proceed"),
                    InlineKeyboardButton("❌ No, Cancel", callback_data="import_confirm:cancel"),
                ]
            ]

            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

            return CONFIRM_IMPORT
        else:
            # No valid entries found
            error_message = "❌ No valid spending entries found in the CSV file."
            if stats["errors"]:
                error_message += f"\n\nFirst 3 errors (of {len(stats['errors'])} total):\n"
                error_message += "\n".join(stats["errors"][:3])

            keyboard = [
                [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
                [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]
                if context.user_data.get("import_from_settings")
                else [],
            ]

            await update.message.reply_text(
                error_message, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
            return UPLOAD_FILE

    except Exception as e:
        error_message = (
            f"❌ Error processing file: {e}\n\nPlease check your file format and try again."
        )

        keyboard = [
            [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
            [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")]
            if context.user_data.get("import_from_settings")
            else [],
        ]

        await update.message.reply_text(
            error_message, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

        await handle_db_error(update, "analyzing spendings", e)
        return UPLOAD_FILE


async def process_csv_import(user_id: int, csv_content: io.StringIO) -> str:
    """Process CSV import and return a result summary."""
    logger.info(f"Starting CSV import for user {user_id}")

    # Initialize statistics
    stats = {
        "success": 0,
        "failed": 0,
        "errors": [],
        "new_categories": set(),
        "new_currencies": set(),
    }

    # Collect user categories and currencies for validation
    try:
        user_categories = set(await db.get_user_categories(user_id))
        user_currencies = set(await db.get_user_currencies(user_id))
    except Exception as e:
        logger.error(f"Error fetching user data for import: {e}")
        return f"Import failed: {e}"

    # Parse CSV file
    reader = csv.reader(csv_content)
    try:
        # Get headers from first row
        headers = [h.strip().lower() for h in next(reader)]

        # Find column indexes
        date_idx = next((i for i, h in enumerate(headers) if "date" in h), None)
        amount_idx = next((i for i, h in enumerate(headers) if "amount" in h), None)
        currency_idx = next((i for i, h in enumerate(headers) if "currency" in h), None)
        category_idx = next((i for i, h in enumerate(headers) if "category" in h), None)
        description_idx = next((i for i, h in enumerate(headers) if "description" in h), None)

        # Validate required columns
        if None in (date_idx, amount_idx, currency_idx, category_idx):
            return "CSV header must include Date, Amount, Currency, and Category columns."

        # Prepare for bulk insert
        valid_spendings = []

        # Process each row
        for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header row
            if not row or len(row) < 4:  # Skip empty rows
                stats["errors"].append(f"Row {row_num}: Empty or incomplete row")
                stats["failed"] += 1
                continue

            try:
                # Extract and validate data
                date_str = row[date_idx].strip()
                try:
                    # Parse date with flexible format support
                    formatted_date = parse_date(date_str)
                except ValueError as e:
                    stats["errors"].append(f"Row {row_num}: {e!s}")
                    stats["failed"] += 1
                    continue

                # Parse amount
                try:
                    amount = float(row[amount_idx].strip())
                    if amount <= 0:
                        stats["errors"].append(f"Row {row_num}: Amount must be positive")
                        stats["failed"] += 1
                        continue
                except ValueError:
                    stats["errors"].append(f"Row {row_num}: Invalid amount value")
                    stats["failed"] += 1
                    continue

                currency = row[currency_idx].strip().upper()
                if not currency or len(currency) != 3:
                    stats["errors"].append(
                        f"Row {row_num}: Invalid currency code (must be 3 letters)"
                    )
                    stats["failed"] += 1
                    continue

                category = row[category_idx].strip().capitalize()
                if not category:
                    stats["errors"].append(f"Row {row_num}: Category cannot be empty")
                    stats["failed"] += 1
                    continue

                # Get description (optional)
                description = (
                    row[description_idx].strip()
                    if description_idx is not None and len(row) > description_idx
                    else ""
                )

                # Track new categories and currencies (we'll add them in batch later)
                if category not in user_categories:
                    user_categories.add(category)
                    stats["new_categories"].add(category)

                if currency not in user_currencies:
                    user_currencies.add(currency)
                    stats["new_currencies"].add(currency)

                # Add to list of valid spendings for bulk insert
                valid_spendings.append(
                    (user_id, description, amount, currency, category, formatted_date)
                )
                stats["success"] += 1

            except Exception as e:
                stats["errors"].append(f"Row {row_num}: Unexpected error: {e}")
                stats["failed"] += 1

        # Now add new categories and currencies
        for category in stats["new_categories"]:
            await db.add_category_to_user(user_id, category)

        for currency in stats["new_currencies"]:
            await db.add_currency_to_user(user_id, currency)

        # Bulk insert all valid spendings at once
        if valid_spendings:
            inserted = await db.bulk_add_spendings(valid_spendings)
            if inserted != stats["success"]:
                logger.warning(f"Bulk insert expected {stats['success']} but inserted {inserted}")

        # Generate result message
        result = f"Import completed: {stats['success']} spendings imported successfully"
        if stats["failed"] > 0:
            result += f", {stats['failed']} failed"

        if stats["new_categories"]:
            result += f"\n\nAdded {len(stats['new_categories'])} new categories: {', '.join(stats['new_categories'])}"

        if stats["new_currencies"]:
            result += f"\n\nAdded {len(stats['new_currencies'])} new currencies: {', '.join(stats['new_currencies'])}"

        if stats["errors"]:
            result += f"\n\nFirst 5 errors (of {len(stats['errors'])} total):\n" + "\n".join(
                stats["errors"][:5]
            )

        log_user_action(
            user_id,
            f"completed CSV import: {stats['success']} successful, {stats['failed']} failed",
        )
        return result
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        return f"Error processing CSV file: {e}"


async def analyze_csv_import(user_id: int, csv_content: io.StringIO) -> tuple[dict, list]:
    """Analyze CSV import data without importing anything.

    Args:
        user_id: The user ID
        csv_content: StringIO with CSV content

    Returns:
        Tuple of (stats dictionary, list of valid spendings)
    """
    logger.info(f"Analyzing CSV import for user {user_id}")

    # Initialize statistics
    stats = {
        "success": 0,
        "failed": 0,
        "errors": [],
        "new_categories": set(),
        "new_currencies": set(),
    }

    # Collect user categories and currencies for validation
    try:
        user_categories = set(await db.get_user_categories(user_id))
        user_currencies = set(await db.get_user_currencies(user_id))
    except Exception as e:
        logger.error(f"Error fetching user data for import analysis: {e}")
        stats["errors"].append(f"Error fetching user data: {e}")
        return stats, []

    # Prepare for validation
    valid_spendings = []

    # Parse CSV file
    reader = csv.reader(csv_content)
    try:
        # Get headers from first row
        headers = [h.strip().lower() for h in next(reader)]

        # Find column indexes
        date_idx = next((i for i, h in enumerate(headers) if "date" in h), None)
        amount_idx = next((i for i, h in enumerate(headers) if "amount" in h), None)
        currency_idx = next((i for i, h in enumerate(headers) if "currency" in h), None)
        category_idx = next((i for i, h in enumerate(headers) if "category" in h), None)
        description_idx = next((i for i, h in enumerate(headers) if "description" in h), None)

        # Validate required columns
        if None in (date_idx, amount_idx, currency_idx, category_idx):
            stats["errors"].append(
                "CSV header must include Date, Amount, Currency, and Category columns."
            )
            return stats, []

        # Process each row
        for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header row
            if not row or len(row) < 4:  # Skip empty rows
                stats["errors"].append(f"Row {row_num}: Empty or incomplete row")
                stats["failed"] += 1
                continue

            try:
                # Extract and validate data
                date_str = row[date_idx].strip()
                try:
                    # Parse date with flexible format support
                    formatted_date = parse_date(date_str)
                except ValueError as e:
                    stats["errors"].append(f"Row {row_num}: {e!s}")
                    stats["failed"] += 1
                    continue

                # Parse amount
                try:
                    amount = float(row[amount_idx].strip())
                    if amount <= 0:
                        stats["errors"].append(f"Row {row_num}: Amount must be positive")
                        stats["failed"] += 1
                        continue
                except ValueError:
                    stats["errors"].append(f"Row {row_num}: Invalid amount value")
                    stats["failed"] += 1
                    continue

                currency = row[currency_idx].strip().upper()
                if not currency or len(currency) != 3:
                    stats["errors"].append(
                        f"Row {row_num}: Invalid currency code (must be 3 letters)"
                    )
                    stats["failed"] += 1
                    continue

                category = row[category_idx].strip().capitalize()
                if not category:
                    stats["errors"].append(f"Row {row_num}: Category cannot be empty")
                    stats["failed"] += 1
                    continue

                # Get description (optional)
                description = (
                    row[description_idx].strip()
                    if description_idx is not None and len(row) > description_idx
                    else ""
                )

                # Track new categories and currencies
                if category not in user_categories:
                    user_categories.add(category)
                    stats["new_categories"].add(category)

                if currency not in user_currencies:
                    user_currencies.add(currency)
                    stats["new_currencies"].add(currency)

                # Add to list of valid spendings
                valid_spendings.append(
                    (user_id, description, amount, currency, category, formatted_date)
                )
                stats["success"] += 1

            except Exception as e:
                stats["errors"].append(f"Row {row_num}: Unexpected error: {e}")
                stats["failed"] += 1

        return stats, valid_spendings
    except Exception as e:
        logger.error(f"CSV analysis error: {e}")
        stats["errors"].append(f"Error processing CSV file: {e}")
        return stats, []


async def handle_import_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle import confirmation choice."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    action = query.data.split(":", 1)[1]

    # If user cancels import
    if action == "cancel":
        log_user_action(user_id, "cancelled import after analysis")
        await query.edit_message_text(
            "Import cancelled. Your data was not imported.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back to Import", callback_data="settings_action:import")]]
            )
            if context.user_data.get("import_from_settings")
            else None,
        )

        # Clear import-related data
        if "csv_import_data" in context.user_data:
            del context.user_data["csv_import_data"]

        if "import_from_settings" in context.user_data:
            del context.user_data["import_from_settings"]

        return ConversationHandler.END

    # If user confirms import
    if action == "proceed":
        log_user_action(user_id, "confirmed import after analysis")

        # Get the stored valid spendings and stats
        if "csv_import_data" not in context.user_data:
            await query.edit_message_text(
                "❌ Import data not found. Please start over.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "« Back to Import", callback_data="settings_action:import"
                            )
                        ]
                    ]
                )
                if context.user_data.get("import_from_settings")
                else None,
            )
            return ConversationHandler.END

        stats = context.user_data["csv_import_data"]["stats"]
        valid_spendings = context.user_data["csv_import_data"]["valid_spendings"]

        try:
            # Process the actual import
            await query.edit_message_text("Importing your data...")

            # Add new categories and currencies
            for category in stats["new_categories"]:
                await db.add_category_to_user(user_id, category)

            for currency in stats["new_currencies"]:
                await db.add_currency_to_user(user_id, currency)

            # Bulk insert all valid spendings at once
            if valid_spendings:
                inserted = await db.bulk_add_spendings(valid_spendings)
                if inserted != stats["success"]:
                    logger.warning(
                        f"Bulk insert expected {stats['success']} but inserted {inserted}"
                    )

            # Generate result message
            result = f"✅ Import completed: {stats['success']} spendings imported successfully"
            if stats["failed"] > 0:
                result += f", {stats['failed']} failed"

            if stats["errors"]:
                result += f"\n\nFirst 5 errors (of {len(stats['errors'])} total):\n" + "\n".join(
                    stats["errors"][:5]
                )

            # Return results to user
            keyboard = (
                [
                    [
                        InlineKeyboardButton(
                            "Import Another File", callback_data="settings_action:import"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "« Back to Settings", callback_data="settings_back:main"
                        )
                    ],
                ]
                if context.user_data.get("import_from_settings")
                else []
            )

            await query.edit_message_text(
                result, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )

            log_user_action(
                user_id,
                f"completed CSV import: {stats['success']} successful, {stats['failed']} failed",
            )

            # Clean up
            del context.user_data["csv_import_data"]
            if "import_from_settings" in context.user_data:
                del context.user_data["import_from_settings"]

            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error during import confirmation: {e}")
            error_message = f"❌ Error importing data: {e}\n\nPlease try again later."

            await query.edit_message_text(
                error_message,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "« Back to Import", callback_data="settings_action:import"
                            )
                        ]
                    ]
                )
                if context.user_data.get("import_from_settings")
                else None,
            )

            await handle_db_error(update, "importing spendings", e)
            return ConversationHandler.END

    # Invalid action
    return ConversationHandler.END


# Create the conversation handler for import
import_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("import", start_import)],
    states={
        UPLOAD_FILE: [
            MessageHandler(filters.Document.ALL, handle_file_upload),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                lambda u, c: u.message.reply_text("Please upload a CSV file"),
            ),
        ],
        CONFIRM_IMPORT: [],  # Handled separately in bot.py via CallbackQueryHandler
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        # Handle callback queries for template download and cancellation
        # These handlers are registered separately in bot.py
    ],
)
