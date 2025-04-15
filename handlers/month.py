from io import BytesIO
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_connection
from utils.logging import logger


async def month_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
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


async def handle_month_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
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
    # data = pd.DataFrame(rows, columns=["category", "total"])

    # Ask user to choose chart type
    buttons = [
        [InlineKeyboardButton("Bar Chart", callback_data=f"chart:bar:{month}:{year}"),
         InlineKeyboardButton("Pie Chart", callback_data=f"chart:pie:{month}:{year}")]
    ]
    logger.info(f"Generated callback data for chart selection: Bar Chart -> chart:bar:{month}:{year}, Pie Chart -> chart:pie:{month}:{year}")
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text("📊 Choose a chart type:", reply_markup=reply_markup)


async def handle_chart_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    logger.info(f"User {user_id} selected a chart type: {query.data}.")
    logger.info(f"Callback data received: {query.data}")

    # Parse callback data
    _, chart_type, month, year = query.data.split(":")
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
    logger.info(f"Data for plotting: {data}")
    await send_plot(query, data, month, year, chart_type)


async def send_plot(query, data: pd.DataFrame, month: int, year: int, chart_type: str = "bar"):
    if chart_type == "bar":
        # Sort data by total spending in descending order
        data = data.sort_values(by='total', ascending=False)

        # Plot the bar chart
        plt.figure(figsize=(12, 8))
        bars = plt.bar(data['category'], data['total'], color=plt.cm.Paired(range(len(data))))

        # Add percentage labels on top of each bar
        total_spending = data['total'].sum()
        for bar, total in zip(bars, data['total']):
            percentage = (total / total_spending) * 100
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f'{percentage:.1f}%',
                ha='center',
                va='bottom',
                fontsize=10
            )

        # Add gridlines for better readability
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Set labels and title
        plt.xlabel('Category', fontsize=12)
        plt.ylabel('Total Spending', fontsize=12)
        plt.title(f"Spending by Category for {datetime(year, month, 1).strftime('%B %Y')}", fontsize=14)
        plt.xticks(rotation=45, ha="right", fontsize=10)
        plt.tight_layout()

    elif chart_type == "pie":
        # Plot the pie chart
        plt.figure(figsize=(10, 8))
        plt.pie(
            data['total'],
            labels=data['category'],
            autopct='%1.1f%%',
            startangle=140,
            colors=plt.cm.Paired(range(len(data)))
        )
        plt.title(f"Spending Distribution for {datetime(year, month, 1).strftime('%B %Y')}", fontsize=14)
        plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular

    logger.info(f"Generating {chart_type} chart for user.")

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    logger.info("Chart generated successfully. Sending chart to user.")

    # Send the chart as a photo
    await query.message.reply_photo(photo=buf)
    buf.close()
    logger.info("Chart sent successfully.")
