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

# Define states for the conversation
CATEGORY_INPUT = range(1)


async def add_category_handler(update: Update, _: CallbackContext):
    log_user_action(update.effective_user.id, "requested to add a category")
    await update.message.reply_text("Please provide a category name to add.")
    return CATEGORY_INPUT


async def handle_category_input(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    category = update.message.text.strip().capitalize()

    if not category:
        await update.message.reply_text("Invalid input. Please provide a valid category name.")
        return CATEGORY_INPUT

    try:
        success = await db.add_category_to_user(user_id, category)
        if success:
            log_user_action(user_id, f"added category '{category}'")
            await update.message.reply_text(f"Category '{category}' has been successfully added!")
        else:
            await update.message.reply_text(
                "Failed to add category. It might already exist or there was an error."
            )
    except Exception as e:
        await handle_db_error(update, f"adding category {category}", e)

    return ConversationHandler.END


add_category_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_category", add_category_handler)],
    states={
        CATEGORY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_input)],
    },
    fallbacks=[CommandHandler(cmd_info["command"], cancel) for cmd_info in BOT_COMMANDS.values()],
)


async def remove_category_handler(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    log_user_action(user_id, "requested to remove a category")

    try:
        categories = await db.get_user_categories(user_id)
        if not categories:
            await update.message.reply_text("You don't have any categories to remove.")
            return

        keyboard = [
            [InlineKeyboardButton(category, callback_data=f"remove_category:{category}")]
            for category in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a category to remove:", reply_markup=reply_markup)
    except Exception as e:
        await handle_db_error(update, "fetching categories", e)


async def handle_remove_category_callback(update: Update, _: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data
    category = data.split(":")[1]

    try:
        success = await db.remove_category_from_user(user_id, category)
        if success:
            log_user_action(user_id, f"removed category '{category}'")
            await query.edit_message_text(f"Category '{category}' has been successfully removed!")
        else:
            await query.edit_message_text(
                "Failed to remove category. It might not exist or there was an error."
            )
    except Exception as e:
        error_msg = f"Error removing category {category}: {e}"
        await query.edit_message_text(f"❌ {error_msg}")
