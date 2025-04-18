from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action


async def choose_main_currency_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    log_user_action(user_id, "requested to set main currency")

    try:
        # Get user's currencies
        currencies = await db.get_user_currencies(user_id)
        if not currencies:
            log_user_action(user_id, "has no currencies to set as main")
            await update.message.reply_text(
                "You don't have any currencies yet. Add currencies first using /add_currency"
            )
            return

        # Get current main currency
        current_main = await db.get_user_main_currency(user_id)
        if current_main:
            log_user_action(user_id, f"current main currency is {current_main}")

        # Create currency selection keyboard
        keyboard = []
        for currency in currencies:
            button_text = f"{currency} {'✓' if currency == current_main else ''}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"main_currency:{currency}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select your main currency:", reply_markup=reply_markup)

    except Exception as e:
        await handle_db_error(update, "fetching currencies", e)


async def handle_main_currency_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    currency = query.data.split(":")[1]
    log_user_action(user_id, f"selected main currency: {currency}")

    try:
        await db.set_user_main_currency(user_id, currency)
        log_user_action(user_id, f"successfully set main currency to {currency}")
        await query.edit_message_text(f"✅ Main currency set to {currency}")

    except Exception as e:
        error_msg = f"Error setting main currency {currency}: {e}"
        await query.edit_message_text(f"❌ {error_msg}")
