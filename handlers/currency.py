from telegram import Update
from telegram.ext import CallbackContext

from db import add_currency_to_user, remove_currency_from_user


def add_currency_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) != 1:
        update.message.reply_text("Please provide a valid 3-letter currency code (e.g., USD, EUR).")
        return

    currency = context.args[0].strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        update.message.reply_text("Please provide a valid 3-letter currency code (e.g., USD, EUR).")
        return

    success = add_currency_to_user(user_id, currency)
    if success:
        update.message.reply_text(f"Currency {currency} has been successfully added!")
    else:
        update.message.reply_text("Failed to add currency. It might already exist or there was an error.")


def remove_currency_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) != 1:
        update.message.reply_text("Please provide a valid 3-letter currency code (e.g., USD, EUR).")
        return

    currency = context.args[0].strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        update.message.reply_text("Please provide a valid 3-letter currency code (e.g., USD, EUR).")
        return

    success = remove_currency_from_user(user_id, currency)
    if success:
        update.message.reply_text(f"Currency {currency} has been successfully removed!")
    else:
        update.message.reply_text("Failed to remove currency. It might not exist or there was an error.")
