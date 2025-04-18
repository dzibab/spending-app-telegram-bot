import csv
from io import StringIO

from telegram import Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action


async def export_spendings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    log_user_action(user_id, "requested to export spendings")
    output = None

    try:
        # Get all spendings as Spending objects
        spendings = await db.export_all_spendings(user_id)
        if not spendings:
            log_user_action(user_id, "attempted to export but has no spendings")
            await update.message.reply_text("You don't have any spendings to export.")
            return

        log_user_action(user_id, f"exporting {len(spendings)} spendings")
        await update.message.reply_text("Preparing your export...")

        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ["Description", "Amount", "Currency", "Category", "Date"]
        writer.writerow(headers)

        # Write data from Spending objects
        for spending in spendings:
            writer.writerow(
                [spending.description, spending.amount, spending.currency, spending.category, spending.date]
            )

        # Prepare file for sending
        output.seek(0)

        # Send file
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=output.getvalue().encode(),
            filename=f"spendings_{user_id}.csv",
            caption="Here are your exported spendings",
        )
        log_user_action(user_id, "successfully exported spendings to CSV")

    except Exception as e:
        await handle_db_error(update, "exporting spendings", e)

    finally:
        # Clean up
        if output:
            try:
                output.close()
            except Exception as e:
                # Just log, but don't report to user as the main operation might have succeeded
                log_user_action(user_id, f"error cleaning up export resources: {e}")
