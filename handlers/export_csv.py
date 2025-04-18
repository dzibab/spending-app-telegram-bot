import csv
from datetime import datetime, timedelta
from io import StringIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import log_user_action
from utils.logging import logger

# Date range options for export
EXPORT_RANGES = {
    "all": "All Time",
    "year": "Current Year",
    "6months": "Last 6 Months",
    "3months": "Last 3 Months",
    "1month": "Last Month",
}


async def export_spendings_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /export command - shows interactive export options."""
    user_id = update.effective_user.id
    log_user_action(user_id, "accessed export options")

    # Show date range selection keyboard
    keyboard = []
    for key, label in EXPORT_RANGES.items():
        keyboard.append([InlineKeyboardButton(label, callback_data=f"export_range:{key}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📤 *Export Your Spending Data*\n\nSelect a time range to export:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_export_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks for export options."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Parse the callback data
    data = query.data.split(":")
    action = data[0]
    value = data[1] if len(data) > 1 else None

    if action == "export_range":
        # User selected a date range
        date_range = value
        log_user_action(user_id, f"selected export range: {date_range}")

        # Process the export directly
        await process_export(update, user_id, date_range)

    elif action == "export_back":
        # Go back to data management menu in settings
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


async def process_export(update: Update, user_id: int, date_range: str) -> None:
    """Process the actual export based on user selections."""
    query = update.callback_query
    output = None
    start_date = None
    end_date = None

    try:
        # Determine the date range
        now = datetime.now()

        if date_range == "all":
            # All time, no filtering
            pass
        elif date_range == "year":
            start_date = datetime(now.year, 1, 1)
        elif date_range == "6months":
            start_date = now - timedelta(days=180)
        elif date_range == "3months":
            start_date = now - timedelta(days=90)
        elif date_range == "1month":
            start_date = now - timedelta(days=30)

        # Get all spendings based on date filter
        await query.edit_message_text("Preparing your export data...\nThis may take a moment.")

        # Use the existing db function or extend it to support date filtering
        if start_date:
            # We need to extend the DB class with this function
            spendings = await db.export_spendings_with_date_range(user_id, start_date, end_date)
        else:
            # Use existing function for "all time"
            spendings = await db.export_all_spendings(user_id)

        if not spendings:
            log_user_action(user_id, "attempted to export but has no spendings in selected range")
            await query.edit_message_text(
                "No spendings found in the selected date range.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "« Back to Export Options", callback_data="export_back:main"
                            )
                        ]
                    ]
                ),
            )
            return

        log_user_action(user_id, f"exporting {len(spendings)} spendings")

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ["Date", "Description", "Amount", "Currency", "Category"]
        writer.writerow(headers)

        # Write data from Spending objects
        for spending in spendings:
            writer.writerow(
                [
                    spending.date,
                    spending.description,
                    spending.amount,
                    spending.currency,
                    spending.category,
                ]
            )

        # Prepare file for sending
        output.seek(0)

        # Format date range for filename
        if date_range == "all":
            date_str = "all_time"
        elif date_range == "year":
            date_str = f"year_{now.year}"
        elif date_range == "6months":
            date_str = f"last_6_months_{now.strftime('%Y%m%d')}"
        elif date_range == "3months":
            date_str = f"last_3_months_{now.strftime('%Y%m%d')}"
        elif date_range == "1month":
            date_str = f"last_month_{now.strftime('%Y%m%d')}"
        else:
            date_str = now.strftime("%Y%m%d")

        # Send file
        await query.edit_message_text("Export ready! Sending your file...")

        await query._bot.send_document(
            chat_id=query.message.chat_id,
            document=output.getvalue().encode(),
            filename=f"spendings_{date_str}.csv",
            caption=f"Here are your exported spendings ({len(spendings)} records)",
        )

        # Show completion message with new export option
        await query.message.reply_text(
            "✅ Export completed successfully!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Export More Data", callback_data="settings_action:export"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "« Back to Settings", callback_data="settings_back:main"
                        )
                    ],
                ]
            ),
        )

        log_user_action(user_id, f"successfully exported {len(spendings)} spendings to CSV")

    except Exception as e:
        log_user_action(user_id, f"error during export: {e}")
        await query.edit_message_text(
            f"❌ Export failed: {e}\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:export")]]
            ),
        )

    finally:
        # Clean up resources
        if output:
            try:
                output.close()
            except Exception as e:
                logger.error(f"Failed to close StringIO: {e}")
