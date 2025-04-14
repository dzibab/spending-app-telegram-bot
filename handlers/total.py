from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
        await update.message.reply_text("📭 No spendings found.")
        return

    # Prepare the result to show to the user
    total_text = "💰 Total spent grouped by currency:\n"
    for currency, total in rows:
        total_text += f"{currency}: {total:.2f}\n"

    await update.message.reply_text(total_text)
