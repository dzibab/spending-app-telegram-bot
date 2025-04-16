import csv
from io import StringIO

from telegram import Update
from telegram.ext import ContextTypes

import db
from utils.logging import logger


async def export_spendings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Processing export request for user {user_id}")

    try:
        # Get all spendings
        spendings = db.export_all_spendings(user_id)
        if not spendings:
            logger.info(f"No spendings found to export for user {user_id}")
            await update.message.reply_text("You don't have any spendings to export.")
            return

        logger.debug(f"Retrieved {len(spendings)} spendings for export")

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ['Description', 'Amount', 'Currency', 'Category', 'Date']
        writer.writerow(headers)
        logger.debug("Created CSV file with headers")

        # Write data
        for spending in spendings:
            writer.writerow(spending)

        # Prepare file for sending
        output.seek(0)
        logger.debug(f"Prepared CSV file with {len(spendings)} rows")

        # Send file
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=output.getvalue().encode(),
            filename=f"spendings_{user_id}.csv",
            caption="Here are your exported spendings"
        )
        logger.info(f"Successfully sent export file to user {user_id}")

    except Exception as e:
        logger.error(f"Error exporting spendings for user {user_id}: {e}")
        await update.message.reply_text("❌ Failed to export spendings. Please try again.")

    finally:
        # Clean up
        try:
            output.close()
            logger.debug("Cleaned up export file resources")
        except:
            pass
