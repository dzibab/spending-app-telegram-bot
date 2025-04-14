from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection


async def list_spendings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT description, amount, currency, category, date
            FROM spendings
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT 10
        """, (user_id,))
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 No spendings found.")
        return

    lines = []
    for desc, amount, currency, cat, dt in rows:
        line = f"{dt} | {amount} {currency} | {cat}"
        if desc:
            line += f" | {desc}"
        lines.append(line)

    await update.message.reply_text("💸 Your last 10 spendings:\n\n" + "\n".join(lines))
