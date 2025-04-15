from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters

from db import add_category_to_user, remove_category_from_user, get_user_categories


# Define states for the conversation
CATEGORY_INPUT = range(1)


async def add_category_handler(update: Update, _: CallbackContext):
    await update.message.reply_text("Please provide a category name to add.")
    return CATEGORY_INPUT


async def handle_category_input(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    category = update.message.text.strip().capitalize()

    if not category:
        await update.message.reply_text("Invalid input. Please provide a valid category name.")
        return CATEGORY_INPUT

    success = add_category_to_user(user_id, category)
    if success:
        await update.message.reply_text(f"Category '{category}' has been successfully added!")
    else:
        await update.message.reply_text("Failed to add category. It might already exist or there was an error.")

    return ConversationHandler.END


add_category_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_category", add_category_handler)],
    states={
        CATEGORY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_input)],
    },
    fallbacks=[],
)


async def remove_category_handler(update: Update, _: CallbackContext):
    user_id = update.effective_user.id
    categories = get_user_categories(user_id)

    if not categories:
        await update.message.reply_text("You don't have any categories to remove.")
        return

    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"remove_category:{category}")]
        for category in categories
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Select a category to remove:", reply_markup=reply_markup)


async def handle_remove_category_callback(update: Update, _: CallbackContext):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("remove_category:"):
        category = data.split(":")[1]
        success = remove_category_from_user(user_id, category)

        if success:
            await query.edit_message_text(f"Category '{category}' has been successfully removed!")
        else:
            await query.edit_message_text("Failed to remove category. It might not exist or there was an error.")
