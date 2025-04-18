from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from constants import BOT_COMMANDS, ITEMS_PER_PAGE
from db import db
from utils.logging import logger
from utils.plotting import create_pagination_buttons

# Define states for the conversation
SEARCH_INPUT = range(1)


def get_current_page_from_markup(reply_markup: InlineKeyboardMarkup) -> int:
    """Extract current page number from the message markup by finding the highlighted button."""
    if not reply_markup or not reply_markup.inline_keyboard:
        return 0

    # Get the pagination row (last row)
    pagination_row = reply_markup.inline_keyboard[-1]

    # Find the button that's highlighted with dashes (current page)
    for button in pagination_row:
        # Current page button text is formatted like "-N-"
        if button.text.startswith("-") and button.text.endswith("-"):
            # Extract the number from "-N-" format
            return int(button.text.strip("-")) - 1  # Convert to 0-based

    return 0  # Default to first page if not found


async def show_search_results(update: Update, user_id: int, query: str = None, amount: float = None, page: int = 0):
    """Show paginated search results."""
    offset = page * ITEMS_PER_PAGE

    # Get total count for pagination
    total_count = await db.count_search_results(user_id, query, amount)
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
    rows = await db.search_spendings(user_id, query, amount, offset, ITEMS_PER_PAGE)
    total_pages = (total_count - 1) // ITEMS_PER_PAGE + 1

    # Create spending buttons
    keyboard = []
    for spending_id, desc, amount, currency, cat, dt in rows:
        button_text = f"{dt} | {amount} {currency} | {cat}"
        if desc:
            button_text += f" | {desc[:20]}"  # Truncate long descriptions
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"search_detail:{spending_id}")])

    # Add pagination buttons
    keyboard.append(create_pagination_buttons(page, total_pages, "search_page"))

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "Search results"
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
        update, user_id, context.user_data.get("search_query"), context.user_data.get("search_amount")
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
            update, user_id, context.user_data.get("search_query"), context.user_data.get("search_amount"), page
        )
    elif data.startswith("search_detail:"):
        # Handle spending details view
        spending_id = int(data.split(":")[1])
        # Get the current page by finding the highlighted button in pagination
        current_page = get_current_page_from_markup(query.message.reply_markup)

        # Get spending details from database
        spending = await db.get_spending_by_id(user_id, spending_id)

        if spending:
            # Show detailed view with back and delete buttons
            text = (
                f"📝 Spending Details:\n\n"
                f"Date: {spending.date}\n"
                f"Amount: {spending.amount} {spending.currency}\n"
                f"Category: {spending.category}\n"
                f"Description: {spending.description or 'No description'}"
            )
            # Add both back and delete buttons
            keyboard = [
                [InlineKeyboardButton("« Back to search results", callback_data=f"search_page:{current_page}")],
                [InlineKeyboardButton("🗑️ Delete", callback_data=f"search_delete:{spending_id}:{current_page}")],
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("❌ Spending not found.")
    elif data.startswith("search_delete:"):
        # Handle deletion of spending from detail view
        parts = data.split(":")
        spending_id = int(parts[1])
        current_page = int(parts[2])

        logger.info(f"User {user_id} deleting spending {spending_id} from search details view")

        # Delete the spending
        success = await db.remove_spending(user_id, spending_id)
        if success:
            logger.info(f"Successfully removed spending {spending_id} for user {user_id}")

            # Calculate total count after deletion to see if we need to adjust the page
            total_count = await db.count_search_results(
                user_id, context.user_data.get("search_query"), context.user_data.get("search_amount")
            )
            items_on_current_page = total_count - (current_page * ITEMS_PER_PAGE)

            # If this was the last item on the current page and we're not on the first page,
            # move to the previous page
            if items_on_current_page <= 0 and current_page > 0:
                current_page -= 1

            # Show confirmation and return to the search results
            await query.edit_message_text("✅ Spending deleted successfully!")
            # Return to search results with potentially adjusted page
            await show_search_results(
                update, user_id, context.user_data.get("search_query"), context.user_data.get("search_amount"), current_page
            )
        else:
            logger.warning(f"Failed to remove spending {spending_id} for user {user_id}")
            await query.edit_message_text(
                "❌ Failed to delete spending. It might have been already removed.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back to search results", callback_data=f"search_page:{current_page}")]]
                ),
            )
    elif data == "search_back":
        # For backward compatibility, handle the old "search_back" callback
        await show_search_results(
            update, user_id, context.user_data.get("search_query"), context.user_data.get("search_amount")
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
    fallbacks=[CommandHandler(cmd_info["command"], cancel) for cmd_info in BOT_COMMANDS.values()],
)
