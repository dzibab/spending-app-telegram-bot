from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters

from db import db
from constants import BOT_COMMANDS


# Define states for the conversation
CURRENCY_INPUT = range(1)


async def add_currency_handler(update: Update, _: CallbackContext):
    await update.message.reply_text("Please provide a valid 3-letter currency code (e.g., USD, EUR).")
    return CURRENCY_INPUT


async def handle_currency_input(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    currency = update.message.text.strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        await update.message.reply_text("Invalid input. Please provide a valid 3-letter currency code (e.g., USD, EUR).")
        return CURRENCY_INPUT

    success = db.add_currency_to_user(user_id, currency)
    if success:
        await update.message.reply_text(f"Currency {currency} has been successfully added!")
    else:
        await update.message.reply_text("Failed to add currency. It might already exist or there was an error.")

    return ConversationHandler.END


async def cancel(update: Update, _: CallbackContext):
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END


add_currency_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_currency", add_currency_handler)],
    states={
        CURRENCY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency_input)],
    },
    fallbacks=[
        CommandHandler(cmd_info["command"], cancel)
        for cmd_info in BOT_COMMANDS.values()
    ],
)


async def remove_currency_handler(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    currencies = db.get_user_currencies(user_id)

    if not currencies:
        await update.message.reply_text("You don't have any currencies to remove.")
        return

    keyboard = [
        [InlineKeyboardButton(currency, callback_data=f"remove_currency:{currency}")]
        for currency in currencies
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Select a currency to remove:", reply_markup=reply_markup)


async def handle_remove_currency_callback(update: Update, _: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    currency = data.split(":")[1]
    success = db.remove_currency_from_user(user_id, currency)

    if success:
        await query.edit_message_text(f"Currency {currency} has been successfully removed!")
    else:
        await query.edit_message_text("Failed to remove currency. It might not exist or there was an error.")
