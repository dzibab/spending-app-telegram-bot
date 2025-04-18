from datetime import datetime

import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from utils.exchange import convert_currency
from utils.logging import logger
from utils.plotting import generate_plot


async def report_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /report command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested spending report.")
    rows = await db.get_unique_month_year_combinations(user_id)

    if not rows:
        logger.info(f"No spendings found for user {user_id}.")
        await update.message.reply_text("📭 No spendings found.")
        return

    buttons = [
        [InlineKeyboardButton(
            f"{datetime(int(y), int(m), 1).strftime('%B %Y')}",
            callback_data=f"month:{m}:{y}"
        )]
        for m, y in rows
    ]
    await update.message.reply_text(
        "📅 Select a month to view the report:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_report_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle month selection for the report."""
    query = update.callback_query
    await query.answer()
    user_id, _, month, year = query.from_user.id, *query.data.split(":")
    month, year = int(month), int(year)
    logger.info(f"User {user_id} selected month: {query.data}.")

    rows = await db.get_spending_data_for_month(user_id, str(year), f"{month:02d}")
    if not rows:
        await query.edit_message_text("📭 No spendings found for this month.")
        return

    buttons = [[
        InlineKeyboardButton("Bar Chart", callback_data=f"chart:bar:{month}:{year}"),
        InlineKeyboardButton("Pie Chart", callback_data=f"chart:pie:{month}:{year}")
    ]]
    await query.edit_message_text(
        text=f"📊 Select the chart type for {datetime(year, month, 1).strftime('%B %Y')}:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_chart_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chart type selection and generate the report."""
    query = update.callback_query
    await query.answer()
    user_id, _, chart_type, month, year = query.from_user.id, *query.data.split(":")
    month, year = int(month), int(year)
    logger.info(f"User {user_id} selected chart type: {query.data}.")

    # Let user know we're working on their chart
    await query.edit_message_text("📊 Generating your chart, please wait...")

    main_currency = await db.get_user_main_currency(user_id)
    if not main_currency:
        await query.edit_message_text("❌ Set your main currency using /main_currency.")
        return

    rows = await db.get_spending_totals_by_category(user_id, str(year), f"{month:02d}")
    if not rows:
        await query.edit_message_text("📭 No spendings found for this month.")
        return

    # Convert all amounts to main currency and aggregate by category
    converted_data = {}
    for category, total, currency in rows:
        try:
            converted_amount = convert_currency(total, currency, main_currency)
            converted_data[category] = converted_data.get(category, 0) + converted_amount
        except Exception as e:
            logger.error(f"Error converting {total} {currency} to {main_currency}: {e}")
            continue

    # Create DataFrame from converted data
    data = pd.DataFrame([
        {"category": cat, "total": amount}
        for cat, amount in converted_data.items()
    ])

    if data.empty:
        await query.edit_message_text("❌ Error converting currencies. Please try again.")
        return

    plot_buffer = generate_plot(data, main_currency, month, year, chart_type)
    await query.message.reply_photo(photo=plot_buffer)
    plot_buffer.close()
