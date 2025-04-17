from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db import db
from utils.logging import logger
from utils.plotting import create_pagination_buttons
from constants import BOT_COMMANDS, ITEMS_PER_PAGE


# Define states for the conversation
SEARCH_INPUT = range(1)


async def show_search_results(update: Update, user_id: int, query: str = None, amount: float = None, page: int = 0):
    """Show paginated search results."""
    offset = page * ITEMS_PER_PAGE

    # Get total count for pagination
    total_count = db.count_search_results(user_id, query, amount)
    if total_count == 0:
        logger.info(f"No matching spendings found for user {user_id}")
        message = "No spendings found"
        if query:
            message += f" matching '{query}'"
        if amount is not None:
            message += f" with amount {amount}"

        if update.callback_query:
            await update.callback_query.edit_message_text(f"📭 {message}.")
        else:
            await update.message.reply_text(f"📭 {message}.")
        return

    # Get paginated search results
    rows = db.search_spendings(user_id, query, amount, offset, ITEMS_PER_PAGE)
    total_pages = (total_count - 1) // ITEMS_PER_PAGE + 1

    # Create spending buttons
    keyboard = []
    for spending_id, desc, amount, currency, cat, dt in rows:
        button_text = f"{dt} | {amount} {currency} | {cat}"
        if desc:
            button_text += f" | {desc[:20]}"  # Truncate long descriptions
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"search_detail:{spending_id}"
        )])

    # Add pagination buttons
    keyboard.append(create_pagination_buttons(page, total_pages, "search_page"))

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"Search results"
    if query:
        message += f" for '{query}'"
    if amount is not None:
        message += f" with amount {amount}"
    message += f" (Page {page + 1}/{total_pages}):"

    if update.callback_query:
        await update.callback_query.edit_message_text(text=message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=message, reply_markup=reply_markup)


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /search command."""
    await update.message.reply_text(
        "Please enter your search term or amount. Examples:\n"
        "- groceries (to search descriptions)\n"
        "- 50.5 (to search for exact amount)\n"
        "You can also use decimal points for amounts."
    )
    return SEARCH_INPUT


async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search input from user."""
    user_id = update.effective_user.id
    search_input = update.message.text.strip()

    # Try to parse as amount first
    try:
        amount = float(search_input)
        context.user_data["search_amount"] = amount
        context.user_data["search_query"] = None
    except ValueError:
        # If not a number, treat as description search
        context.user_data["search_amount"] = None
        context.user_data["search_query"] = search_input

    await show_search_results(
        update,
        user_id,
        context.user_data.get("search_query"),
        context.user_data.get("search_amount")
    )
    return ConversationHandler.END


async def handle_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks for search pagination and spending details."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = query.data
    if data == "noop":
        # Do nothing for ellipsis buttons
        return
    elif data.startswith("search_page:"):
        # Handle pagination
        page = int(data.split(":")[1])
        await show_search_results(
            update,
            user_id,
            context.user_data.get("search_query"),
            context.user_data.get("search_amount"),
            page
        )
    elif data.startswith("search_detail:"):
        # Handle spending details view
        spending_id = int(data.split(":")[1])
        # Get spending details from database
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT description, amount, currency, category, date
                FROM spendings
                WHERE id = ? AND user_id = ?
            """, (spending_id, user_id))
            spending = cursor.fetchone()

        if spending:
            desc, amount, currency, category, date = spending
            # Show detailed view with a back button
            text = (
                f"📝 Spending Details:\n\n"
                f"Date: {date}\n"
                f"Amount: {amount} {currency}\n"
                f"Category: {category}\n"
                f"Description: {desc or 'No description'}"
            )
            # Add a back button that returns to search
            keyboard = [[InlineKeyboardButton(
                "« Back to search results",
                callback_data="search_back"
            )]]
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Spending not found.")
    elif data == "search_back":
        # Return to search results
        await show_search_results(
            update,
            user_id,
            context.user_data.get("search_query"),
            context.user_data.get("search_amount")
        )


async def cancel(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Cancel the search operation."""
    await update.message.reply_text("Search canceled.")
    return ConversationHandler.END


# Create the conversation handler for search
search_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("search", start_search)],
    states={
        SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input)],
    },
    fallbacks=[
        CommandHandler(cmd_info["command"], cancel)
        for cmd_info in BOT_COMMANDS.values()
    ],
)