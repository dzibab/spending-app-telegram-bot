from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import db
from utils.logging import logger
from utils.plotting import create_pagination_buttons
from constants import ITEMS_PER_PAGE


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


async def show_spendings_page(update: Update, user_id: int, page: int = 0):
    """Show a page of spendings with navigation buttons."""
    offset = page * ITEMS_PER_PAGE

    # Get total count for pagination
    total_count = await db.get_spendings_count(user_id)
    if total_count == 0:
        logger.info(f"No spendings found for user {user_id}.")
        if update.callback_query:
            await update.callback_query.edit_message_text("📭 No spendings found.")
        else:
            await update.message.reply_text("📭 No spendings found.")
        return

    # Get paginated data
    rows = await db.get_paginated_spendings(user_id, offset, ITEMS_PER_PAGE)
    total_pages = (total_count - 1) // ITEMS_PER_PAGE + 1

    # If current page is beyond total pages, adjust to last available page
    if page >= total_pages:
        page = max(0, total_pages - 1)
        offset = page * ITEMS_PER_PAGE
        # Refetch data with adjusted page
        if total_count > 0:
            rows = await db.get_paginated_spendings(user_id, offset, ITEMS_PER_PAGE)
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
            callback_data=f"list_detail:{spending_id}"
        )])

    # Add pagination buttons
    keyboard.append(create_pagination_buttons(page, total_pages, "list_page"))

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"Your spendings (Page {page + 1}/{total_pages}):"

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def list_spendings_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handler for /list command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested a list of spendings.")
    await show_spendings_page(update, user_id)


async def handle_list_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks for list pagination and spending details."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = query.data
    if data == "noop":
        # Do nothing for ellipsis buttons
        return
    elif data.startswith("list_page:"):
        # Handle pagination
        page = int(data.split(":")[1])
        await show_spendings_page(update, user_id, page)
    elif data.startswith("list_detail:"):
        # Handle spending details view
        spending_id = int(data.split(":")[1])
        # Get the current page by finding the highlighted button in pagination
        current_page = get_current_page_from_markup(query.message.reply_markup)

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
                [InlineKeyboardButton("« Back to list", callback_data=f"list_page:{current_page}")],
                [InlineKeyboardButton("🗑️ Delete", callback_data=f"list_delete:{spending_id}:{current_page}")]
            ]
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Spending not found.")
    elif data.startswith("list_delete:"):
        # Handle deletion of spending from detail view
        parts = data.split(":")
        spending_id = int(parts[1])
        current_page = int(parts[2])

        logger.info(f"User {user_id} deleting spending {spending_id} from details view")

        # Delete the spending
        success = await db.remove_spending(user_id, spending_id)
        if success:
            logger.info(f"Successfully removed spending {spending_id} for user {user_id}")

            # Calculate total count after deletion to see if we need to adjust the page
            total_count = await db.get_spendings_count(user_id)
            items_on_current_page = total_count - (current_page * ITEMS_PER_PAGE)

            # If this was the last item on the current page and we're not on the first page,
            # move to the previous page
            if items_on_current_page <= 0 and current_page > 0:
                current_page -= 1

            # Show confirmation and return to the list
            await query.edit_message_text("✅ Spending deleted successfully!")
            # Small delay to show the confirmation message
            await show_spendings_page(update, user_id, current_page)
        else:
            logger.warning(f"Failed to remove spending {spending_id} for user {user_id}")
            await query.edit_message_text(
                "❌ Failed to delete spending. It might have been already removed.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to list", callback_data=f"list_page:{current_page}")
                ]])
            )
