"""Common pagination utilities for spending lists and search results."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_current_page_from_markup(reply_markup: InlineKeyboardMarkup) -> int:
    """Extract current page number from the message markup by finding the highlighted button."""
    if not reply_markup or not reply_markup.inline_keyboard:
        return 0
    # Get the pagination row (last row)
    pagination_row = reply_markup.inline_keyboard[-1]
    # Find the button that's highlighted with dashes (current page)
    for button in pagination_row:
        if button.text.startswith("-") and button.text.endswith("-"):
            return int(button.text.strip("-")) - 1  # Convert to 0-based
    return 0  # Default to first page if not found


def create_pagination_buttons(current_page: int, total_pages: int, callback_prefix: str) -> list[InlineKeyboardButton]:
    """Create pagination buttons with first and last pages always visible.
    Current page is highlighted with dashes and is non-clickable.
    This function works with ITEMS_PER_PAGE constant from constants.py
    which defines how many items are shown per page.
    Args:
        current_page: Current page number (0-based)
        total_pages: Total number of pages based on ITEMS_PER_PAGE constant
        callback_prefix: Prefix for the callback data (e.g., 'list_page' or 'remove_page')
    Returns:
        List of InlineKeyboardButton objects with formatted pagination
    """
    buttons = []
    if total_pages <= 1:
        buttons.append(InlineKeyboardButton("-1-", callback_data="noop"))
        return buttons
    if current_page == 0:
        buttons.append(InlineKeyboardButton("-1-", callback_data="noop"))
    else:
        buttons.append(InlineKeyboardButton("1", callback_data=f"{callback_prefix}:0"))
    if current_page > 2:
        buttons.append(InlineKeyboardButton("...", callback_data="noop"))
    for page in range(max(1, current_page - 1), min(total_pages - 1, current_page + 2)):
        if page == 0 or page == total_pages - 1:
            continue
        button_text = f"-{page + 1}-" if page == current_page else str(page + 1)
        callback_data = "noop" if page == current_page else f"{callback_prefix}:{page}"
        buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))
    if current_page < total_pages - 3:
        buttons.append(InlineKeyboardButton("...", callback_data="noop"))
    if total_pages > 1:
        if current_page == total_pages - 1:
            buttons.append(InlineKeyboardButton(f"-{total_pages}-", callback_data="noop"))
        else:
            buttons.append(InlineKeyboardButton(str(total_pages), callback_data=f"{callback_prefix}:{total_pages - 1}"))
    return buttons
