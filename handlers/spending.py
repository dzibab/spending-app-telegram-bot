from datetime import datetime, date

from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db import db
from constants import BOT_COMMANDS
from utils.logging import logger


# Define states for the conversation
DESCRIPTION, AMOUNT, CURRENCY, CATEGORY, DATE = range(5)


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("Invalid date format. Use YYYY-MM-DD or DD-MM-YYYY.")


async def start_add(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} initiated adding a spending.")

    # Add a 'skip' button for the description state
    keyboard = [["Skip"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Please provide a description:",
        reply_markup=reply_markup,
        )
    return DESCRIPTION


async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    if description.lower() != "skip":
        context.user_data["description"] = description
    else:
        context.user_data["description"] = ""
    await update.message.reply_text("Enter the amount:", reply_markup=ReplyKeyboardRemove())
    return AMOUNT


async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["amount"] = amount

        # Fetch user-specific currencies
        user_id = update.effective_user.id
        currencies = db.get_user_currencies(user_id)

        # Create a keyboard with currency options
        keyboard = [[c] for c in currencies]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

        await update.message.reply_text(
            "Enter the currency:",
            reply_markup=reply_markup
        )
        return CURRENCY
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:")
        return AMOUNT


async def handle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    currencies = db.get_user_currencies(user_id)

    currency = update.message.text.upper()
    if currency not in currencies:
        keyboard = [[c] for c in currencies]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "❌ Invalid currency code. Please select a valid currency from the options below:",
            reply_markup=reply_markup
        )
        return CURRENCY
    context.user_data["currency"] = currency

    # Fetch user-specific categories
    categories = db.get_user_categories(user_id)

    # Add categories as buttons
    keyboard = [[category] for category in categories]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Enter the category:", reply_markup=reply_markup)
    return CATEGORY


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    context.user_data["category"] = category

    # Add a 'today' button for the date state
    keyboard = [["Today"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Enter the date or press 'Today' for today's date:",
        reply_markup=reply_markup,
        )
    return DATE


async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_input = update.message.text
    try:
        if date_input.lower() == "today":
            spend_date = date.today()
        else:
            spend_date = parse_date(date_input)
        context.user_data["date"] = spend_date

        # Proceed to save the spending to the database
        await write_spending_to_db(update, context)
        return ConversationHandler.END
    except ValueError as ve:
        await update.message.reply_text(f"❌ {ve}\nPlease enter the date again:")
        return DATE
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return ConversationHandler.END


async def write_spending_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        description = context.user_data["description"]
        amount = context.user_data["amount"]
        currency = context.user_data["currency"]
        category = context.user_data["category"]
        spend_date = context.user_data["date"]

        spending_id = db.add_spending(user_id, description, amount, currency, category, spend_date.isoformat())
        logger.info(f"User {user_id} added spending ID {spending_id}: {amount} {currency} for {category} on {spend_date}.")

        await update.message.reply_text(
            f"✅ Spending added successfully!\n"
            f"ID: {spending_id}\n"
            f"Description: {description or 'None'}\n"
            f"Amount: {amount} {currency}\n"
            f"Category: {category}\n"
            f"Date: {spend_date}",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Error while saving spending for user {user_id}: {e}")
        await update.message.reply_text(f"❌ Error while saving to the database: {e}")


async def cancel(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Define the ConversationHandler
add_spending_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_spending", start_add)],
    states={
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency)],
        CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
    },
    fallbacks=[
        CommandHandler(cmd_info["command"], cancel)
        for cmd_info in BOT_COMMANDS.values()
    ],
)


async def show_spendings_to_remove(update: Update, user_id: int, page: int = 0):
    """Show a page of spendings with navigation buttons for removal."""
    ITEMS_PER_PAGE = 10  # Show fewer items since each item will be a button
    offset = page * ITEMS_PER_PAGE

    # Get total count for pagination
    total_count = db.get_spendings_count(user_id)
    if total_count == 0:
        logger.info(f"No spendings found for user {user_id}.")
        if update.callback_query:
            await update.callback_query.edit_message_text("📭 No spendings found.")
        else:
            await update.message.reply_text("📭 No spendings found.")
        return

    # Get paginated data
    rows = db.get_paginated_spendings(user_id, offset, ITEMS_PER_PAGE)
    total_pages = (total_count - 1) // ITEMS_PER_PAGE + 1

    # Create spending buttons
    keyboard = []
    for spending_id, desc, amount, currency, cat, dt in rows:
        # Format the spending information
        button_text = f"{dt} | {amount} {currency} | {cat}"
        if desc:
            button_text += f" | {desc[:20]}"  # Truncate long descriptions
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"remove:{spending_id}"
        )])

    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"remove_page:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"remove_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"Select a spending to remove (Page {page + 1}/{total_pages}):"

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def remove_spending_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handler for /remove command - shows list of spendings to remove."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} accessed spending removal interface")
    await show_spendings_to_remove(update, user_id)


async def handle_remove_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks for spending removal and pagination."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # Parse callback data
    data = query.data
    if data.startswith("remove_page:"):
        # Handle pagination
        page = int(data.split(":")[1])
        await show_spendings_to_remove(update, user_id, page)
    elif data.startswith("remove:"):
        # Handle spending removal
        spending_id = int(data.split(":")[1])
        if db.remove_spending(user_id, spending_id):
            logger.info(f"Successfully removed spending {spending_id} for user {user_id}")
            # Show updated list after removal
            await show_spendings_to_remove(update, user_id, 0)
        else:
            logger.warning(f"Failed to remove spending {spending_id} for user {user_id}")
            await query.edit_message_text("❌ Failed to remove spending. It might have been already removed.")
