from io import BytesIO
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_connection
from utils.logging import logger


async def month(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested month selection.")

    # Query to fetch unique month-year combinations
    query = """
        SELECT DISTINCT strftime('%m', date) as month, strftime('%Y', date) as year
        FROM spendings
        WHERE user_id = ?
        ORDER BY year DESC, month DESC
    """
    with get_connection() as conn:
        cursor = conn.execute(query, (user_id,))
        rows = cursor.fetchall()

    if not rows:
        logger.info(f"No spendings found for user {user_id} to display months.")
        await update.message.reply_text("📭 No spendings found.")
        return

    logger.info(f"User {user_id} retrieved {len(rows)} unique month-year combinations.")

    # Create inline keyboard buttons
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{datetime(int(year), int(month), 1).strftime('%B %Y')}",
                callback_data=f"month:{month}:{year}",
            )
        ]
        for month, year in rows
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text("📅 Select a month:", reply_markup=reply_markup)


async def handle_month_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    logger.info(f"User {user_id} selected a month: {query.data}.")

    # Parse callback data
    _, month, year = query.data.split(":")
    month = int(month)
    year = int(year)

    # Query to fetch spending data for the selected month and year
    spending_query = """
        SELECT category, SUM(amount) as total
        FROM spendings
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category
    """
    with get_connection() as conn:
        cursor = conn.execute(spending_query, (user_id, str(year), f"{month:02d}"))
        rows = cursor.fetchall()

    if not rows:
        logger.info(f"No spendings found for user {user_id} in the selected month.")
        await query.edit_message_text("📭 No spendings found for this month.")
        return

    logger.info(f"User {user_id} retrieved spending data for the selected month: {rows}.")

    # Prepare data for plotting
    data = pd.DataFrame(rows, columns=["category", "total"])
    await send_plot(query, data, month, year)


async def send_plot(query, data: pd.DataFrame, month: int, year: int):
    # Plot the chart
    plt.figure(figsize=(10, 6))
    plt.bar(data['category'], data['total'], color='skyblue')
    plt.xlabel('Category')
    plt.ylabel('Total Spending')
    plt.title(f"Spending by Category for {datetime(year, month, 1).strftime('%B %Y')}")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Send the chart as a photo
    await query.message.reply_photo(photo=buf)
    buf.close()
