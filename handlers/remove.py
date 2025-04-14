from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Usage: /remove <spending_id>")
        return

    spending_id = int(args[0])
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM spendings WHERE id = ? AND user_id = ?",
            (spending_id, user_id)
        )
        if cursor.rowcount == 0:
            await update.message.reply_text("❌ Not found.")
        else:
            await update.message.reply_text("✅ Spending removed.")
