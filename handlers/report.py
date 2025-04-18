from datetime import datetime

import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action
from utils.exchange import convert_currency
from utils.logging import logger
from utils.plotting import ChartError, generate_plot


async def report_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /report command."""
    user_id = update.effective_user.id
    log_user_action(user_id, "requested spending report")

    try:
        rows = await db.get_unique_month_year_combinations(user_id)

        if not rows:
            log_user_action(user_id, "has no spending data for reports")
            await update.message.reply_text("📭 No spendings found.")
            return

        buttons = [
            [
                InlineKeyboardButton(
                    f"{datetime(int(y), int(m), 1).strftime('%B %Y')}",
                    callback_data=f"month:{m}:{y}",
                )
            ]
            for m, y in rows
        ]
        await update.message.reply_text(
            "📅 Select a month to view the report:", reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await handle_db_error(update, "fetching report data", e)


async def handle_report_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle month selection for the report."""
    query = update.callback_query
    await query.answer()

    user_id, _, month, year = query.from_user.id, *query.data.split(":")
    month, year = int(month), int(year)
    log_user_action(user_id, f"selected month {month}/{year} for report")

    try:
        rows = await db.get_spending_data_for_month(user_id, str(year), f"{month:02d}")
        if not rows:
            log_user_action(user_id, f"has no spending data for {month}/{year}")
            await query.edit_message_text("📭 No spendings found for this month.")
            return

        buttons = [
            [
                InlineKeyboardButton("Bar Chart", callback_data=f"chart:bar:{month}:{year}"),
                InlineKeyboardButton("Pie Chart", callback_data=f"chart:pie:{month}:{year}"),
            ]
        ]
        await query.edit_message_text(
            text=f"📊 Select the chart type for {datetime(year, month, 1).strftime('%B %Y')}:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception as e:
        error_msg = f"Error fetching data for {month}/{year}: {e}"
        await query.edit_message_text(f"❌ {error_msg}")


async def handle_chart_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chart type selection and generate the report."""
    query = update.callback_query
    await query.answer()

    user_id, _, chart_type, month, year = query.from_user.id, *query.data.split(":")
    month, year = int(month), int(year)
    log_user_action(user_id, f"requested {chart_type} chart for {month}/{year}")

    # Let user know we're working on their chart
    await query.edit_message_text("📊 Generating your chart, please wait...")

    try:
        main_currency = await db.get_user_main_currency(user_id)
        if not main_currency:
            log_user_action(user_id, "has no main currency set for reports")
            await query.edit_message_text("❌ Set your main currency using /main_currency.")
            return

        # Use the new optimized method that returns comprehensive report data
        report_data = await db.get_monthly_report_data(user_id, str(year), f"{month:02d}")

        if not report_data["categories"]:
            log_user_action(user_id, f"has no spending data for {month}/{year}")
            await query.edit_message_text("📭 No spendings found for this month.")
            return

        # Convert all amounts to main currency and aggregate by category
        converted_data = {}
        conversion_errors = []

        # Process data from each currency in the report
        for currency in report_data["currencies"]:
            currency_data = report_data["by_currency"][currency]
            for category, amount in currency_data["categories"].items():
                try:
                    converted_amount = convert_currency(amount, currency, main_currency)
                    converted_data[category] = converted_data.get(category, 0) + converted_amount
                except Exception as e:
                    error_detail = f"Error converting {amount} {currency} to {main_currency}: {e}"
                    logger.error(error_detail)
                    conversion_errors.append(error_detail)
                    continue

        # Create DataFrame from converted data
        data = pd.DataFrame(
            [{"category": cat, "total": amount} for cat, amount in converted_data.items()]
        )

        if data.empty:
            log_user_action(user_id, "couldn't convert currency data for chart")
            await query.edit_message_text("❌ Error converting currencies. Please try again.")
            return

        try:
            plot_buffer = generate_plot(data, main_currency, month, year, chart_type)
            await query.message.reply_photo(photo=plot_buffer)
            log_user_action(
                user_id, f"successfully generated {chart_type} chart for {month}/{year}"
            )
            plot_buffer.close()
        except ChartError as ce:
            error_msg = f"Chart generation error: {ce}"
            await query.edit_message_text(f"❌ {error_msg}")

    except Exception as e:
        error_msg = f"Error generating chart: {e}"
        await query.edit_message_text(f"❌ {error_msg}")
