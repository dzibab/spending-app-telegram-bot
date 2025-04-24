import csv
from datetime import datetime, timedelta
from io import StringIO
import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import TimedOut

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

# Constants for export limits
MAX_EXPORT_FILE_SIZE = 45 * 1024 * 1024  # 45MB (Telegram limit is 50MB but leave buffer)
MAX_RECORDS_PER_FILE = 50000  # Maximum records per file for splitting large exports
DB_QUERY_TIMEOUT = 60  # Database query timeout in seconds


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

    elif action == "export_continue":
        # User confirmed to continue with large export
        date_range = value
        logger.info(f"User {user_id} confirmed large export for range: {date_range}")
        log_user_action(user_id, f"confirmed large export for range: {date_range}")

        # Update message to show processing status
        await query.edit_message_text("Processing your large export. This will take some time...")

        # Handle as normal export but with special handling for large datasets
        now = datetime.now()
        start_date = None
        end_date = None

        # Set date range based on selection
        if date_range == "year":
            start_date = datetime(now.year, 1, 1)
        elif date_range == "6months":
            start_date = now - timedelta(days=180)
        elif date_range == "3months":
            start_date = now - timedelta(days=90)
        elif date_range == "1month":
            start_date = now - timedelta(days=30)

        # Proceed with large export
        try:
            # Get expected record count
            expected_count = await asyncio.wait_for(
                get_record_count(user_id, start_date, end_date), timeout=DB_QUERY_TIMEOUT
            )

            # Generate and send export
            result = await generate_and_send_export(
                query, user_id, date_range, start_date, end_date, expected_count
            )

            if result["success"]:
                # Show completion message
                await query.message.reply_text(
                    f"✅ Large export completed successfully! {result['message']}",
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
                log_user_action(
                    user_id,
                    f"successfully exported {result['count']} spendings to CSV (large export)",
                )
            else:
                # Handle failure
                await query.edit_message_text(
                    f"⚠️ Export issue: {result['message']}",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "« Try Again", callback_data="settings_action:export"
                                )
                            ]
                        ]
                    ),
                )
                log_user_action(user_id, f"large export completed with issues: {result['message']}")

        except asyncio.TimeoutError:
            logger.error(f"Large export timed out for user {user_id}")
            log_user_action(user_id, "error during large export: Timed out")
            await query.edit_message_text(
                "❌ Export failed: The operation timed out for this large dataset.\n"
                "Please try exporting a smaller date range.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:export")]]
                ),
            )
        except Exception as e:
            logger.error(f"Large export failed for user {user_id}: {e}", exc_info=True)
            log_user_action(user_id, f"error during large export: {e}")
            await query.edit_message_text(
                f"❌ Export failed: {e}\n\nPlease try again with a smaller date range.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:export")]]
                ),
            )

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
    progress_message = None

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

        # Get count of records to export first to determine approach
        count_result = await asyncio.wait_for(
            get_record_count(user_id, start_date, end_date), timeout=DB_QUERY_TIMEOUT
        )
        expected_count = count_result
        logger.info(f"Found {expected_count} total records to export for user {user_id}")

        # Show a more detailed progress message for large exports
        progress_msg = "Preparing your export data..."
        if expected_count > 5000:
            progress_msg += f"\nProcessing {expected_count} records. This may take a moment."

        await query.edit_message_text(progress_msg)
        logger.debug(f"Notified user {user_id} that export is being prepared")

        # For extremely large datasets, warn the user
        if expected_count > MAX_RECORDS_PER_FILE:
            logger.warning(
                f"User {user_id} is exporting a very large dataset: {expected_count} records"
            )
            # Update message to inform user about large export
            await query.edit_message_text(
                f"⚠️ You're exporting a large dataset ({expected_count:,} records).\n"
                f"This may be split into multiple files and take some time to process.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Continue", callback_data=f"export_continue:{date_range}"
                            )
                        ],
                        [InlineKeyboardButton("Cancel", callback_data="export_back:main")],
                    ]
                ),
            )
            # We'll continue when the user confirms via callback in handle_export_callback
            return

        # Check if no records found immediately
        if expected_count == 0:
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

        # Proceed with export
        result = await generate_and_send_export(
            query, user_id, date_range, start_date, end_date, expected_count
        )

        if result["success"]:
            # Show completion message with new export option
            await query.message.reply_text(
                f"✅ Export completed successfully! {result['message']}",
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
            log_user_action(user_id, f"successfully exported {result['count']} spendings to CSV")
            logger.info(
                f"Export successfully completed for user {user_id}: {result['count']} records"
            )
        else:
            # Handle partial failure
            await query.message.reply_text(
                f"⚠️ Export completed with some issues: {result['message']}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:export")]]
                ),
            )
            log_user_action(user_id, f"export completed with issues: {result['message']}")

    except asyncio.TimeoutError:
        logger.error(f"Export timed out for user {user_id} when querying database")
        log_user_action(user_id, "error during export: Timed out when querying database")
        await query.edit_message_text(
            "❌ Export failed: The operation timed out. Please try exporting a smaller date range.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:export")]]
            ),
        )
    except Exception as e:
        logger.error(f"Export failed for user {user_id}: {str(e)}", exc_info=True)
        log_user_action(user_id, f"error during export: {e}")
        await query.edit_message_text(
            f"❌ Export failed: {e}\n\nPlease try again later or with a smaller date range.",
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


async def get_record_count(user_id: int, start_date=None, end_date=None) -> int:
    """Get count of records for export with date filters.

    Args:
        user_id: User ID
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        Count of records matching criteria
    """
    logger.debug(f"Counting records for user {user_id} with date filters")

    async with db.connection() as cursor:
        params = [user_id]
        sql = "SELECT COUNT(*) FROM spendings WHERE user_id = ?"

        # Add date filters
        if start_date:
            sql += " AND date(date) >= date(?)"
            params.append(start_date.strftime("%Y-%m-%d"))

        if end_date:
            sql += " AND date(date) <= date(?)"
            params.append(end_date.strftime("%Y-%m-%d"))

        # Execute the count query
        await cursor.execute(sql, params)
        row = await cursor.fetchone()
        count = row[0] if row else 0

        return count


async def generate_and_send_export(
    query, user_id, date_range, start_date, end_date, expected_count
):
    """Generate and send the export file with timeout protection.

    Args:
        query: The callback query from Telegram
        user_id: User ID
        date_range: Selected date range string
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        expected_count: Expected number of records

    Returns:
        Dictionary with results: {'success': bool, 'count': int, 'message': str}
    """
    logger.debug(f"Generating export for user {user_id} with {expected_count} records")
    now = datetime.now()

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

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    headers = ["Date", "Description", "Amount", "Currency", "Category"]
    writer.writerow(headers)

    total_count = 0
    try:
        # Apply timeout to the chunked export process
        if start_date:
            total_count = await asyncio.wait_for(
                process_export_in_chunks(output, writer, user_id, start_date, end_date),
                timeout=DB_QUERY_TIMEOUT * 2,  # Allow more time for actual data processing
            )
        else:
            # Use all-time export with streaming
            total_count = await asyncio.wait_for(
                process_export_all_streaming(output, writer, user_id), timeout=DB_QUERY_TIMEOUT * 2
            )

        # Check if we got any records
        if total_count == 0:
            return {
                "success": True,
                "count": 0,
                "message": "No records found in the selected date range.",
            }

        # Prepare file for sending
        output.seek(0)
        file_data = output.getvalue().encode()
        file_size = len(file_data)

        # Check if file is too large for Telegram
        if file_size > MAX_EXPORT_FILE_SIZE:
            logger.warning(f"Export file for user {user_id} is too large: {file_size} bytes")
            return {
                "success": False,
                "count": total_count,
                "message": "The export file is too large for Telegram. Please try exporting a smaller date range.",
            }

        # Update user on progress
        await query.edit_message_text("Export ready! Sending your file...")

        # Send the file
        await query._bot.send_document(
            chat_id=query.message.chat_id,
            document=file_data,
            filename=filename,
            caption=f"Here are your exported spendings ({total_count:,} records)",
        )

        return {
            "success": True,
            "count": total_count,
            "message": f"Exported {total_count:,} records successfully.",
        }

    except asyncio.TimeoutError:
        logger.error(f"Export generation timed out for user {user_id}")
        return {
            "success": False,
            "count": 0,
            "message": "The operation timed out. Try exporting a smaller date range.",
        }
    except Exception as e:
        logger.error(f"Error during export generation for user {user_id}: {e}", exc_info=True)
        return {"success": False, "count": total_count, "message": f"Error during export: {e}"}
    finally:
        # Clean up resources
        if output:
            try:
                output.close()
            except Exception:
                pass
