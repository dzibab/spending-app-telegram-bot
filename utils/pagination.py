"""Common pagination utilities for spending lists and search results."""
import inspect

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from constants import ITEMS_PER_PAGE
from db import db
from utils.logging import logger


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


def format_spending_button_text(spending_tuple) -> str:
    """Format the button text for a spending entry.

    Args:
        spending_tuple: Tuple containing (id, description, amount, currency, category, date)

    Returns:
        Formatted button text
    """
    _, desc, amount, currency, cat, dt = spending_tuple
    button_text = f"{dt} | {amount} {currency} | {cat}"
    if desc:
        button_text += f" | {desc[:20]}"  # Truncate long descriptions
    return button_text


async def handle_no_results(update: Update, message: str) -> None:
    """Handle case when no results are available.

    Args:
        update: The update object
        message: The message to display
    """
    if update.callback_query:
        await update.callback_query.edit_message_text(f"📭 {message}.")
    else:
        await update.message.reply_text(f"📭 {message}.")


async def format_spending_details(spending) -> str:
    """Format spending details for display.

    Args:
        spending: The Spending object

    Returns:
        Formatted text with spending details
    """
    return (
        f"📝 Spending Details:\n\n"
        f"Date: {spending.date}\n"
        f"Amount: {spending.amount} {spending.currency}\n"
        f"Category: {spending.category}\n"
        f"Description: {spending.description or 'No description'}"
    )


async def handle_delete_spending(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    spending_id: int,
    current_page: int,
    return_callback_prefix: str,
    get_item_count_fn,
    show_results_fn,
    **kwargs
) -> None:
    """Handle spending deletion logic common to both list and search views.

    Args:
        update: The update object
        context: The context object
        user_id: The user ID
        spending_id: The spending ID to delete
        current_page: The current page number
        return_callback_prefix: The callback prefix for the return button
        get_item_count_fn: Function to get count of items after deletion
        show_results_fn: Function to show results after deletion
        kwargs: Additional arguments to pass to get_item_count_fn and show_results_fn
    """
    logger.info(f"User {user_id} deleting spending {spending_id}")

    # Delete the spending
    success = await db.remove_spending(user_id, spending_id)

    if success:
        logger.info(f"Successfully removed spending {spending_id} for user {user_id}")

        # Calculate total count after deletion to see if we need to adjust the page
        total_count = await get_item_count_fn(user_id, **kwargs)
        items_on_current_page = total_count - (current_page * ITEMS_PER_PAGE)

        # If this was the last item on the current page and we're not on the first page,
        # move to the previous page
        if items_on_current_page <= 0 and current_page > 0:
            current_page -= 1

        # Show confirmation
        await update.callback_query.edit_message_text("✅ Spending deleted successfully!")

        # Inspect the show_results_fn signature to determine if it expects 'page' or explicit positional ordering
        sig = inspect.signature(show_results_fn)
        param_names = list(sig.parameters.keys())

        # Check if the third parameter (after update and user_id) is named 'page'
        if len(param_names) >= 3 and param_names[2] == 'page':
            # Return to results with potentially adjusted page using named parameter
            await show_results_fn(update, user_id, page=current_page, **kwargs)
        else:
            # Add current_page to kwargs if not already present
            if 'page' not in kwargs:
                kwargs['page'] = current_page
            await show_results_fn(update, user_id, **kwargs)
    else:
        logger.warning(f"Failed to remove spending {spending_id} for user {user_id}")
        back_button = InlineKeyboardButton(
            "« Back", callback_data=f"{return_callback_prefix}:{current_page}"
        )
        await update.callback_query.edit_message_text(
            "❌ Failed to delete spending. It might have been already removed.",
            reply_markup=InlineKeyboardMarkup([[back_button]])
        )
