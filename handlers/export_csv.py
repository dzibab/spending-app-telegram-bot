import csv
from datetime import datetime, timedelta
from io import StringIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db, Spending
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
    logger.info(f"User {user_id} initiated export process")
    log_user_action(user_id, "accessed export options")

    # Show date range selection keyboard
    keyboard = []
    for key, label in EXPORT_RANGES.items():
        keyboard.append([InlineKeyboardButton(label, callback_data=f"export_range:{key}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.debug(f"Showing export options menu to user {user_id}")

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

    logger.debug(f"Export callback: action={action}, value={value} for user {user_id}")

    if action == "export_range":
        # User selected a date range
        date_range = value
        logger.info(f"User {user_id} selected export range: {date_range}")
        log_user_action(user_id, f"selected export range: {date_range}")

        # Process the export directly
        await process_export(update, user_id, date_range)

    elif action == "export_back":
        # Go back to data management menu in settings
        logger.debug(f"User {user_id} navigated back from export options")
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
    """Process the actual export based on user selections with streaming for large datasets."""
    query = update.callback_query
    output = None
    start_date = None
    end_date = None

    logger.info(f"Beginning export process for user {user_id} with date range '{date_range}'")

    try:
        # Determine the date range
        now = datetime.now()

        if date_range == "all":
            # All time, no filtering
            logger.debug(f"User {user_id} exporting all spending records")
            pass
        elif date_range == "year":
            start_date = datetime(now.year, 1, 1)
            logger.debug(f"User {user_id} exporting records from {start_date.isoformat()}")
        elif date_range == "6months":
            start_date = now - timedelta(days=180)
            logger.debug(f"User {user_id} exporting records from {start_date.isoformat()}")
        elif date_range == "3months":
            start_date = now - timedelta(days=90)
            logger.debug(f"User {user_id} exporting records from {start_date.isoformat()}")
        elif date_range == "1month":
            start_date = now - timedelta(days=30)
            logger.debug(f"User {user_id} exporting records from {start_date.isoformat()}")

        # Get all spendings based on date filter
        await query.edit_message_text(
            "Preparing your export data...\nThis may take a moment for large datasets."
        )
        logger.debug(f"Notified user {user_id} that export is being prepared")

        # Create CSV in memory before fetching data to prepare headers
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ["Date", "Description", "Amount", "Currency", "Category"]
        writer.writerow(headers)
        logger.debug(f"Created CSV headers: {headers}")

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

        filename = f"spendings_{date_str}.csv"
        logger.debug(f"Export filename will be: {filename}")

        # Use the optimized streaming approach
        if start_date:
            logger.debug(f"Using date-filtered export for user {user_id}")
            total_count = await process_export_in_chunks(
                output, writer, user_id, start_date, end_date
            )
        else:
            # Use existing function for "all time" with streaming
            logger.debug(f"Using all-time export for user {user_id}")
            total_count = await process_export_all_streaming(output, writer, user_id)

        logger.info(f"Export completed for user {user_id}: {total_count} records processed")

        if total_count == 0:
            logger.info(f"No records found for user {user_id} with date range '{date_range}'")
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

        log_user_action(user_id, f"exporting {total_count} spendings")

        # Prepare file for sending
        output.seek(0)

        # Send file
        await query.edit_message_text("Export ready! Sending your file...")
        logger.debug(f"Sending CSV export to user {user_id}")

        await query._bot.send_document(
            chat_id=query.message.chat_id,
            document=output.getvalue().encode(),
            filename=filename,
            caption=f"Here are your exported spendings ({total_count} records)",
        )
        logger.debug(f"CSV file sent to user {user_id}")

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

        log_user_action(user_id, f"successfully exported {total_count} spendings to CSV")
        logger.info(f"Export successfully completed for user {user_id}: {total_count} records")

    except Exception as e:
        logger.error(f"Export failed for user {user_id}: {str(e)}", exc_info=True)
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
                logger.debug(f"Closed StringIO resource for user {user_id}'s export")
            except Exception as e:
                logger.error(f"Failed to close StringIO for user {user_id}: {e}")


async def process_export_in_chunks(output_stream, writer, user_id, start_date, end_date=None):
    """Process export in chunks to handle large datasets efficiently.

    Args:
        output_stream: The StringIO instance for writing CSV data
        writer: CSV writer object
        user_id: User ID
        start_date: Start date filter
        end_date: Optional end date filter

    Returns:
        Total number of records exported
    """
    logger.debug(
        f"Starting chunked export for user {user_id} from {start_date} to {end_date or 'now'}"
    )
    total_count = 0
    chunk_size = 1000

    # Begin execution with a chunked query approach
    async with db.connection() as cursor:
        params = [user_id]
        sql = "SELECT * FROM spendings WHERE user_id = ?"

        # Add date filters
        if start_date:
            sql += " AND date(date) >= date(?)"
            params.append(start_date.strftime("%Y-%m-%d"))

        if end_date:
            sql += " AND date(date) <= date(?)"
            params.append(end_date.strftime("%Y-%m-%d"))

        # Count total records first (for progress reporting)
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        await cursor.execute(count_sql, params)
        row = await cursor.fetchone()
        expected_count = row[0] if row else 0
        logger.info(f"Found {expected_count} records to export for user {user_id}")

        if expected_count == 0:
            return 0

        # Sort by date descending
        sql += " ORDER BY date DESC, id DESC"

        # Process in chunks
        offset = 0
        while True:
            chunk_sql = f"{sql} LIMIT {chunk_size} OFFSET {offset}"
            logger.debug(f"Executing chunk query with offset {offset}: {chunk_sql}")
            await cursor.execute(chunk_sql, params)
            rows = await cursor.fetchall()

            if not rows:
                logger.debug(f"No more rows found at offset {offset}")
                break

            # Write chunk to CSV
            chunk_count = 0
            for row in rows:
                spending = Spending.from_row(tuple(row))
                writer.writerow(
                    [
                        spending.date,
                        spending.description,
                        spending.amount,
                        spending.currency,
                        spending.category,
                    ]
                )
                total_count += 1
                chunk_count += 1

            logger.debug(
                f"Processed chunk of {chunk_count} records, total so far: {total_count}/{expected_count}"
            )

            if len(rows) < chunk_size:
                logger.debug(f"Last chunk processed (only {len(rows)} rows)")
                break

            offset += chunk_size

    logger.info(f"Completed chunked export for user {user_id}: {total_count} records exported")
    return total_count


async def process_export_all_streaming(output_stream, writer, user_id):
    """Export all data with memory-efficient streaming approach.

    Args:
        output_stream: StringIO object for the CSV data
        writer: CSV writer using the output_stream
        user_id: User ID to export data for

    Returns:
        Count of exported records
    """
    logger.debug(f"Starting all-time streaming export for user {user_id}")
    total_count = 0
    chunk_size = 1000

    # Begin execution with a chunked query approach
    async with db.connection() as cursor:
        # Count total records first
        await cursor.execute("SELECT COUNT(*) FROM spendings WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        expected_count = row[0] if row else 0
        logger.info(f"Found {expected_count} total records to export for user {user_id}")

        if expected_count == 0:
            return 0

        # Process in chunks
        offset = 0
        while True:
            logger.debug(f"Fetching chunk at offset {offset}")
            await cursor.execute(
                """
                SELECT *
                FROM spendings
                WHERE user_id = ?
                ORDER BY date DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, chunk_size, offset),
            )
            rows = await cursor.fetchall()

            if not rows:
                logger.debug(f"No more rows found at offset {offset}")
                break

            # Write chunk to CSV
            chunk_count = 0
            for row in rows:
                spending = Spending.from_row(tuple(row))
                writer.writerow(
                    [
                        spending.date,
                        spending.description,
                        spending.amount,
                        spending.currency,
                        spending.category,
                    ]
                )
                total_count += 1
                chunk_count += 1

            logger.debug(
                f"Processed chunk of {chunk_count} records, total so far: {total_count}/{expected_count}"
            )

            if len(rows) < chunk_size:
                logger.debug(f"Last chunk processed (only {len(rows)} rows)")
                break

            offset += chunk_size

    logger.info(f"Completed all-time export for user {user_id}: {total_count} records exported")
    return total_count
