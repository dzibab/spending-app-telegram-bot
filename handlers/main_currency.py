from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_user_currencies, set_user_main_currency


async def choose_main_currency_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Fetch the list of currencies for the user
    currencies = get_user_currencies(user_id)

    if not currencies:
        await update.message.reply_text("You don't have any currencies set up.")
        return

    # Create inline keyboard buttons for each currency
    buttons = [
        [InlineKeyboardButton(currency, callback_data=f"main_currency:{currency}")]
        for currency in currencies
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text("Choose your main currency:", reply_markup=reply_markup)


async def handle_main_currency_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Parse the selected currency from callback data
    _, selected_currency = query.data.split(":")
    user_id = query.from_user.id

    # Save the selected currency as the user's main currency
    set_user_main_currency(user_id, selected_currency)

    await query.edit_message_text(f"Your main currency has been set to {selected_currency}.")
