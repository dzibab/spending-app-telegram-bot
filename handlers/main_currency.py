from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from utils.logging import logger


async def choose_main_currency_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested to set main currency")

    try:
        # Get user's currencies
        currencies = await db.get_user_currencies(user_id)
        if not currencies:
            logger.warning(f"No currencies found for user {user_id}")
            await update.message.reply_text(
                "You don't have any currencies yet. Add currencies first using /add_currency"
            )
            return

        logger.debug(f"Retrieved {len(currencies)} currencies for user {user_id}")
        current_main = await db.get_user_main_currency(user_id)
        if current_main:
            logger.debug(f"Current main currency for user {user_id}: {current_main}")

        # Create currency selection keyboard
        keyboard = []
        for currency in currencies:
            button_text = f"{currency} {'✓' if currency == current_main else ''}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"main_currency:{currency}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select your main currency:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error while setting up main currency selection for user {user_id}: {e}")
        await update.message.reply_text("❌ Failed to load currencies. Please try again.")


async def handle_main_currency_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    currency = query.data.split(":")[1]
    logger.info(f"User {user_id} selected main currency: {currency}")

    try:
        await db.set_user_main_currency(user_id, currency)
        logger.info(f"Successfully set main currency to {currency} for user {user_id}")
        await query.edit_message_text(f"✅ Main currency set to {currency}")

    except Exception as e:
        logger.error(f"Error setting main currency {currency} for user {user_id}: {e}")
        await query.edit_message_text(
            f"❌ Failed to set main currency to {currency}. Please try again."
        )
