from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection
from utils.logging import logger


async def total_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested total spendings.")
    args = context.args

    # Prepare filters for optional category or currency
    category = None
    if len(args) == 1:
        category = args[0]
    elif len(args) == 2:
        category, _ = args  # We ignore second argument (currency) for grouping purposes

    # Prepare the SQL query for sum grouped by currency
    query = """
        SELECT currency, SUM(amount)
        FROM spendings
        WHERE user_id = ?
    """
    params = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY currency"

    # Execute the query
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        logger.info(f"No spendings found for user {user_id} to calculate totals.")
        await update.message.reply_text("📭 No spendings found.")
        return

    logger.info(f"User {user_id} retrieved total spendings grouped by currency: {rows}.")

    # Prepare the result to show to the user in a formatted table
    total_text = "💰 Total spent grouped by currency:\n\n"
    total_text += "Currency   | Total\n"
    total_text += "---------- | ----------\n"
    for currency, total in rows:
        total_text += f"{currency:<10} | {total:>10.2f}\n"

    await update.message.reply_text(f"```\n{total_text}\n```", parse_mode="Markdown")
