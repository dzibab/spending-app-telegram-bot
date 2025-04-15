from datetime import datetime

import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import (
    get_connection,
    get_user_main_currency,
    get_unique_month_year_combinations,
    get_spending_data_for_month,
)
from utils.logging import logger
from utils.exchange import convert_currency
from utils.plotting import generate_plot


async def month_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested month selection.")
    rows = get_unique_month_year_combinations(user_id)

    if not rows:
        logger.info(f"No spendings found for user {user_id}.")
        await update.message.reply_text("📭 No spendings found.")
        return

    buttons = [
        [InlineKeyboardButton(f"{datetime(int(y), int(m), 1).strftime('%B %Y')}", callback_data=f"month:{m}:{y}")]
        for m, y in rows
    ]
    await update.message.reply_text("📅 Select a month:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_month_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id, _, month, year = query.from_user.id, *query.data.split(":")
    month, year = int(month), int(year)
    logger.info(f"User {user_id} selected month: {query.data}.")

    main_currency = get_user_main_currency(user_id)
    if not main_currency:
        await query.edit_message_text("❌ Set your main currency using /main_currency.")
        return

    rows = get_spending_data_for_month(user_id, str(year), f"{month:02d}")
    if not rows:
        await query.edit_message_text("📭 No spendings found for this month.")
        return

    converted_data = {}
    for category, total, currency in rows:
        try:
            converted_data[category] = converted_data.get(category, 0) + convert_currency(total, currency, main_currency)
        except Exception as e:
            logger.error(f"Error converting {total} {currency} to {main_currency}: {e}")

    buttons = [[
        InlineKeyboardButton("Bar Chart", callback_data=f"chart:bar:{month}:{year}"),
        InlineKeyboardButton("Pie Chart", callback_data=f"chart:pie:{month}:{year}")
    ]]
    await query.edit_message_text(
        text=f"📊 Select the chart type for {datetime(year, month, 1).strftime('%B %Y')}:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_chart_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id, _, chart_type, month, year = query.from_user.id, *query.data.split(":")
    month, year = int(month), int(year)
    logger.info(f"User {user_id} selected chart type: {query.data}.")

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) as total
            FROM spendings
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            GROUP BY category
            """, (user_id, str(year), f"{month:02d}")
        ).fetchall()

    if not rows:
        await query.edit_message_text("📭 No spendings found for this month.")
        return

    data = pd.DataFrame(rows, columns=["category", "total"])
    plot_buffer = generate_plot(data, get_user_main_currency(user_id), month, year, chart_type)
    await query.message.reply_photo(photo=plot_buffer)
    plot_buffer.close()
