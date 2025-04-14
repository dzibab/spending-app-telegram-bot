from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    # Check for optional category or currency filters
    category = None
    currency = None
    if len(args) == 1:
        category = args[0]
    elif len(args) == 2:
        category, currency = args

    # Prepare the SQL query
    query = "SELECT SUM(amount) FROM spendings WHERE user_id = ?"
    params = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    if currency:
        query += " AND currency = ?"
        params.append(currency)

    # Execute the query
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        result = cursor.fetchone()

    # Check if there are any results
    total = result[0] if result[0] is not None else 0

    # Return the total spent
    filters = []
    if category:
        filters.append(f"Category: {category}")
    if currency:
        filters.append(f"Currency: {currency}")

    filter_text = " | ".join(filters) if filters else "All spendings"
    await update.message.reply_text(f"💰 Total spent ({filter_text}): {total:.2f}")
