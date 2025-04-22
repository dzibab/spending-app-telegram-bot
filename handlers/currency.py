from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from constants import BOT_COMMANDS
from db import db
from handlers.common import cancel, handle_db_error, log_user_action
from utils.currency_utils import add_currency_to_user, remove_currency, set_main_currency
from utils.validation import validate_currency_code

# Define states for the conversation
CURRENCY_INPUT = range(1)


async def add_currency_handler(update: Update, _: CallbackContext):
    log_user_action(update.effective_user.id, "requested to add a currency")
    await update.message.reply_text(
        "Please provide a valid 3-letter currency code (e.g., USD, EUR).\n\n"
        "The code must be exactly 3 letters, representing an ISO 4217 currency code."
    )
    return CURRENCY_INPUT


async def handle_currency_input(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    currency = update.message.text.strip()

    # Use validation utility for format validation
    is_valid, error_message = validate_currency_code(currency)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_message}\n\nPlease provide a valid 3-letter currency code (e.g., USD, EUR)."
        )
        return CURRENCY_INPUT

    # Convert to uppercase for consistency
    currency = currency.upper()

    # Use the shared business logic utility
    success, message = await add_currency_to_user(user_id, currency)

    if success:
        await update.message.reply_text(f"✅ {message}")
    else:
        await update.message.reply_text(f"❌ {message}")

    return ConversationHandler.END


add_currency_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_currency", add_currency_handler)],
    states={
        CURRENCY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency_input)],
    },
    fallbacks=[CommandHandler(cmd_info["command"], cancel) for cmd_info in BOT_COMMANDS.values()],
)


async def remove_currency_handler(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    log_user_action(user_id, "requested to remove a currency")

    try:
        currencies = await db.get_user_currencies(user_id)
        if not currencies:
            await update.message.reply_text("You don't have any currencies to remove.")
            return

        # Get current main currency to mark it
        main_currency = await db.get_user_main_currency(user_id)

        keyboard = []
        for currency in currencies:
            label = f"{currency} {'✓' if currency == main_currency else ''}"
            keyboard.append(
                [InlineKeyboardButton(label, callback_data=f"remove_currency:{currency}")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Select a currency to remove:"
            + ("\n\n*Note: Your main currency is marked with ✓*" if main_currency else ""),
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    except Exception as e:
        await handle_db_error(update, "fetching currencies", e)


async def handle_remove_currency_callback(update: Update, _: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    currency = data.split(":")[1]

    # Validate currency format (redundant but good practice)
    is_valid, error_message = validate_currency_code(currency)
    if not is_valid:
        await query.edit_message_text(f"❌ {error_message}")
        return

    try:
        # Check if currency is set as main currency
        current_main = await db.get_user_main_currency(user_id)
        if current_main == currency:
            # If removing main currency, confirm with the user
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Yes, Remove", callback_data=f"confirm_remove_currency:{currency}"
                    )
                ],
                [InlineKeyboardButton("No, Cancel", callback_data="cancel_remove_currency")],
            ]
            await query.edit_message_text(
                f"⚠️ {currency} is your main currency. Are you sure you want to remove it?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Not a main currency, proceed with removal (don't archive, completely remove for backward compatibility)
        success, message, _ = await remove_currency(user_id, currency, archive=False)

        if success:
            await query.edit_message_text(f"✅ {message}")
        else:
            await query.edit_message_text(f"❌ {message}")
    except Exception as e:
        error_msg = f"Error removing currency {currency}: {e}"
        await query.edit_message_text(f"❌ {error_msg}")


async def handle_confirm_remove_currency(update: Update, _: CallbackContext):
    """Handle confirmation for removing a main currency"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    currency = data.split(":")[1]

    # Use shared business logic to remove the currency (don't archive for backward compatibility)
    success, message, _ = await remove_currency(user_id, currency, archive=False)

    if success:
        await query.edit_message_text(f"✅ {message}")
    else:
        await query.edit_message_text(f"❌ {message}")


async def handle_cancel_remove_currency(update: Update, _: CallbackContext):
    """Handle cancelation of currency removal"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✅ Currency removal canceled. Your main currency remains unchanged."
    )
