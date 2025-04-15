import textwrap

from telegram import Update
from telegram.ext import ContextTypes

from db import get_recent_spendings
from utils.logging import logger


async def list_spendings_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested a list of spendings.")

    rows = get_recent_spendings(user_id)
    if not rows:
        logger.info(f"No spendings found for user {user_id}.")
        await update.message.reply_text("📭 No spendings found.")
        return

    logger.info(f"User {user_id} retrieved {len(rows)} spendings.")

    # Determine column widths based on the longest element in each column
    col_widths = {
        "date": max(len(row[4]) for row in rows),
        "amount": max(len(f"{row[1]:.2f}") for row in rows),
        "currency": max(len(row[2]) for row in rows),
        "category": max(len(row[3]) for row in rows),
        "description": max(len(row[0]) for row in rows if row[0]) if any(row[0] for row in rows) else 0,
    }

    lines = []
    for desc, amount, currency, cat, dt in rows:
        line = f"{dt:<{col_widths['date']}} | {amount:>{col_widths['amount']}.2f} {currency:<{col_widths['currency']}} | {cat:<{col_widths['category']}}"
        if desc:
            line += f" | {desc:<{col_widths['description']}}"
        lines.append(line)

    formatted_message = "💸 Your last 10 spendings:\n\n" + "\n".join(lines)
    await update.message.reply_text(f"```\n{textwrap.dedent(formatted_message)}\n```", parse_mode="Markdown")
