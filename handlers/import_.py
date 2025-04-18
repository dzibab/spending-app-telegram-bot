"""Handler for importing spending data from CSV files."""

import csv
import io

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from db import db
from handlers.common import cancel, handle_db_error, log_user_action
from utils.date_utils import parse_date

# Define states for the conversation
UPLOAD_FILE = range(1)


async def start_import(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for /import command to start the import conversation."""
    user_id = update.effective_user.id
    log_user_action(user_id, "initiated importing spendings from CSV")

    await update.message.reply_text(
        "Please upload a CSV file with your spending data.\n\n"
        "The file should contain these columns:\n"
        "- Date (required, formats: YYYY-MM-DD, DD-MM-YYYY with delimiters -, / or .)\n"
        "- Amount (required, numeric value)\n"
        "- Currency (required, currency code)\n"
        "- Category (required)\n"
        "- Description (optional)\n\n"
        "Use /cancel to abort the import."
    )
    return UPLOAD_FILE


async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the uploaded CSV file."""
    user_id = update.effective_user.id
    log_user_action(user_id, "uploaded a file for import")

    # Check if a file was provided
    if not update.message.document:
        await update.message.reply_text("Please upload a CSV file. Use /cancel to abort.")
        return UPLOAD_FILE

    # Check if the file is a CSV
    if not update.message.document.file_name.lower().endswith(".csv"):
        await update.message.reply_text("Please upload a CSV file, not another file type. Use /cancel to abort.")
        return UPLOAD_FILE

    await update.message.reply_text("Analyzing your file. This may take a moment...")

    try:
        # Get the file from Telegram
        file = await context.bot.get_file(update.message.document.file_id)
        bytes_content = await file.download_as_bytearray()
        csv_content = io.StringIO(bytes_content.decode("utf-8"))

        # Process the CSV file
        result = await process_csv_import(user_id, csv_content)

        # Return results to user
        await update.message.reply_text(result, reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END
    except Exception as e:
        await handle_db_error(update, "importing spendings", e)
        return ConversationHandler.END


async def process_csv_import(user_id: int, csv_content: io.StringIO) -> str:
    """Process the CSV file content and import the spendings.

    Args:
        user_id: The user's Telegram ID
        csv_content: StringIO object with CSV content

    Returns:
        Result message to show to the user
    """
    # Statistics for reporting
    stats = {"success": 0, "failed": 0, "new_categories": set(), "new_currencies": set(), "errors": []}

    log_user_action(user_id, "processing CSV import")

    try:
        # Get existing user categories and currencies
        user_categories = set(await db.get_user_categories(user_id))
        user_currencies = set(await db.get_user_currencies(user_id))

        # Read CSV
        reader = csv.reader(csv_content)

        # Parse header and check required columns
        try:
            headers = [h.strip().lower() for h in next(reader)]
            required_fields = ["date", "amount", "currency", "category"]
            found_fields = [field for field in required_fields if field in headers]

            # Verify that all required fields are present
            if len(found_fields) < len(required_fields):
                missing = set(required_fields) - set(found_fields)
                return f"❌ Import failed: Missing required columns: {', '.join(missing)}"

            # Get column indexes
            date_idx = headers.index("date")
            amount_idx = headers.index("amount")
            currency_idx = headers.index("currency")
            category_idx = headers.index("category")
            # Description is optional
            description_idx = headers.index("description") if "description" in headers else None

        except StopIteration:
            return "❌ Import failed: CSV file is empty or has no headers."
        except ValueError:
            return "❌ Import failed: CSV format is incorrect or missing required columns."

        # Process each row
        for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header row
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
                    stats["errors"].append(f"Row {row_num}: {str(e)}")
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
                    stats["errors"].append(f"Row {row_num}: Invalid currency code (must be 3 letters)")
                    stats["failed"] += 1
                    continue

                category = row[category_idx].strip().capitalize()
                if not category:
                    stats["errors"].append(f"Row {row_num}: Category cannot be empty")
                    stats["failed"] += 1
                    continue

                # Get description (optional)
                description = (
                    row[description_idx].strip() if description_idx is not None and len(row) > description_idx else ""
                )

                # Add new categories and currencies as needed
                if category not in user_categories:
                    await db.add_category_to_user(user_id, category)
                    user_categories.add(category)
                    stats["new_categories"].add(category)

                if currency not in user_currencies:
                    await db.add_currency_to_user(user_id, currency)
                    user_currencies.add(currency)
                    stats["new_currencies"].add(currency)

                # Add the spending to the database
                await db.add_spending(user_id, description, amount, currency, category, formatted_date)
                stats["success"] += 1

            except Exception as e:
                stats["errors"].append(f"Row {row_num}: {str(e)}")
                stats["failed"] += 1

    except Exception as e:
        log_user_action(user_id, f"error during CSV import: {e}")
        return f"❌ Import failed: {str(e)}"

    # Create result message
    result = f"✅ Import completed: {stats['success']} spendings imported successfully"

    if stats["failed"] > 0:
        result += f", {stats['failed']} failed"

    if stats["new_categories"]:
        result += f"\n\nAdded {len(stats['new_categories'])} new categories: {', '.join(stats['new_categories'])}"

    if stats["new_currencies"]:
        result += f"\n\nAdded {len(stats['new_currencies'])} new currencies: {', '.join(stats['new_currencies'])}"

    if stats["errors"] and len(stats["errors"]) <= 5:
        result += "\n\nErrors:\n" + "\n".join(stats["errors"])
    elif stats["errors"]:
        result += f"\n\nFirst 5 errors (of {len(stats['errors'])} total):\n" + "\n".join(stats["errors"][:5])

    log_user_action(user_id, f"completed CSV import: {stats['success']} successful, {stats['failed']} failed")
    return result


# Create the conversation handler for import
import_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("import", start_import)],
    states={
        UPLOAD_FILE: [
            MessageHandler(filters.Document.ALL, handle_file_upload),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text("Please upload a CSV file")
            ),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
