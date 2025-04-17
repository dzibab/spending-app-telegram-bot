from datetime import datetime, date

from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db import db
from constants import BOT_COMMANDS, ITEMS_PER_PAGE
from utils.logging import logger
from utils.plotting import create_pagination_buttons


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

        db.add_spending(user_id, description, amount, currency, category, spend_date.isoformat())
        logger.info(f"User {user_id} added spending: {amount} {currency} for {category} on {spend_date}.")

        await update.message.reply_text(
            f"✅ Spending added successfully!\n"
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


def get_current_page_from_markup(reply_markup: InlineKeyboardMarkup) -> int:
    """Extract current page number from the message markup by finding the highlighted button."""
    if not reply_markup or not reply_markup.inline_keyboard:
        return 0

    # Get the pagination row (last row)
    pagination_row = reply_markup.inline_keyboard[-1]

    # Find the button that's highlighted with dashes (current page)
    for button in pagination_row:
        # Current page button text is formatted like "-N-"
        if button.text.startswith('-') and button.text.endswith('-'):
            # Extract the number from "-N-" format
            return int(button.text.strip('-')) - 1  # Convert to 0-based

    return 0  # Default to first page if not found


async def show_spendings_to_remove(update: Update, user_id: int, page: int = 0):
    """Show a page of spendings with navigation buttons for removal."""
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

    # Calculate total pages
    total_pages = (total_count - 1) // ITEMS_PER_PAGE + 1

    # If current page is beyond total pages, adjust to last available page
    if page >= total_pages:
        page = max(0, total_pages - 1)
        offset = page * ITEMS_PER_PAGE

    # Get paginated data
    rows = db.get_paginated_spendings(user_id, offset, ITEMS_PER_PAGE)

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

    # Add pagination buttons
    keyboard.append(create_pagination_buttons(page, total_pages, "remove_page"))

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
    if data == "noop":
        # Do nothing for ellipsis buttons
        return
    elif data.startswith("remove_page:"):
        # Handle pagination
        page = int(data.split(":")[1])
        await show_spendings_to_remove(update, user_id, page)
    elif data.startswith("remove:"):
        # Handle spending removal
        spending_id = int(data.split(":")[1])
        # Get the current page before removing the spending
        current_page = get_current_page_from_markup(query.message.reply_markup)

        if db.remove_spending(user_id, spending_id):
            logger.info(f"Successfully removed spending {spending_id} for user {user_id}")

            # Calculate if we need to move to previous page
            total_count = db.get_spendings_count(user_id)
            items_on_current_page = total_count - (current_page * ITEMS_PER_PAGE)

            # If this was the last item on the current page and we're not on the first page,
            # move to the previous page
            if items_on_current_page <= 0 and current_page > 0:
                current_page -= 1

            # Show updated list after removal
            await show_spendings_to_remove(update, user_id, current_page)
        else:
            logger.warning(f"Failed to remove spending {spending_id} for user {user_id}")
            await query.edit_message_text("❌ Failed to remove spending. It might have been already removed.")
