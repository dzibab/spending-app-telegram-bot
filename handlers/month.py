from io import BytesIO
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_connection, get_user_main_currency
from utils.logging import logger
from utils.exchange import convert_currency


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

    main_currency = get_user_main_currency(user_id)

    if not main_currency:
        logger.info(f"No main currency set for user {user_id}.")
        await query.edit_message_text("❌ Please set your main currency using /main_currency before proceeding.")
        return

    # Query to fetch spending data for the selected month and year
    spending_query = """
        SELECT category, SUM(amount) as total, currency
        FROM spendings
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category, currency
    """
    with get_connection() as conn:
        cursor = conn.execute(spending_query, (user_id, str(year), f"{month:02d}"))
        rows = cursor.fetchall()

    if not rows:
        logger.info(f"No spendings found for user {user_id} in the selected month.")
        await query.edit_message_text("📭 No spendings found for this month.")
        return

    logger.info(f"User {user_id} retrieved spending data for the selected month: {rows}.")

    # Convert all amounts to the main currency
    converted_data = {}
    for category, total, currency in rows:
        try:
            converted_total = convert_currency(total, currency, main_currency)
            if category in converted_data:
                converted_data[category] += converted_total
            else:
                converted_data[category] = converted_total
        except Exception as e:
            logger.error(f"Error converting {total} {currency} to {main_currency}: {e}")

    # Prepare data for plotting
    data = pd.DataFrame(list(converted_data.items()), columns=["category", "total"])
    logger.info(f"Data for plotting: {data}")

    # Add buttons for chart type selection
    buttons = [
        [
            InlineKeyboardButton("Bar Chart", callback_data=f"chart:bar:{month}:{year}"),
            InlineKeyboardButton("Pie Chart", callback_data=f"chart:pie:{month}:{year}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text=f"📊 Select the chart type for {datetime(year, month, 1).strftime('%B %Y')}:",
        reply_markup=reply_markup
    )


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

    main_currency = get_user_main_currency(user_id)

    # Prepare data for plotting
    data = pd.DataFrame(rows, columns=["category", "total"])
    logger.info(f"Data for plotting: {data}")
    await send_plot(query, data, month, year, main_currency, chart_type)


def plot_bar_chart(data: pd.DataFrame, main_currency: str, month: int, year: int):
    # Sort data by total spending in descending order
    data = data.sort_values(by='total', ascending=False)

    # Plot the bar chart
    plt.figure(figsize=(12, 8))
    bars = plt.bar(data['category'], data['total'], color=plt.cm.Paired(range(len(data))))

    # Add percentage labels and total spending on top of each bar
    total_spending = data['total'].sum()
    for bar, (category, total) in zip(bars, data.itertuples(index=False)):
        percentage = (total / total_spending) * 100
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f'{total:.2f} {main_currency}\n({percentage:.1f}%)',
            ha='center',
            va='bottom',
            fontsize=10
        )

    # Add gridlines for better readability
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Set labels and title
    plt.xlabel('Category', fontsize=12)
    plt.ylabel(f'Total Spending ({main_currency})', fontsize=12)
    plt.title(f"Spending by Category for {datetime(year, month, 1).strftime('%B %Y')}\nTotal: {total_spending:.2f} {main_currency}", fontsize=14)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.tight_layout()


def plot_pie_chart(data: pd.DataFrame, main_currency: str, month: int, year: int):
    # Calculate total spending
    total_spending = data['total'].sum()

    # Plot the pie chart
    plt.figure(figsize=(10, 8))
    wedges, texts, autotexts = plt.pie(
        data['total'],
        labels=data['category'],
        autopct=lambda p: f'{p:.1f}%\n({(p * total_spending / 100):.2f} {main_currency})',
        startangle=140,
        colors=plt.cm.Paired(range(len(data)))
    )

    # Style the text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(9)

    plt.title(f"Spending Distribution for {datetime(year, month, 1).strftime('%B %Y')}\nTotal: {total_spending:.2f} {main_currency}", fontsize=14)
    plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular


async def send_plot(query, data: pd.DataFrame, month: int, year: int, main_currency: str, chart_type: str = "bar"):
    if chart_type == "bar":
        plot_bar_chart(data, main_currency, month, year)
    elif chart_type == "pie":
        plot_pie_chart(data, main_currency, month, year)

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
