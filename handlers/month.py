from datetime import datetime

import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_connection, get_user_main_currency
from utils.logging import logger
from utils.exchange import convert_currency
from utils.plotting import generate_plot


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

    # Generate the plot using the `generate_plot` function
    plot_buffer = generate_plot(data, main_currency, month, year, chart_type)

    logger.info(f"Generating {chart_type} chart for user.")

    # Send the chart as a photo
    await query.message.reply_photo(photo=plot_buffer)
    plot_buffer.close()
    logger.info("Chart sent successfully.")
