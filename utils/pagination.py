"""Common pagination utilities for spending lists and search results."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.logging import logger


def get_current_page_from_markup(reply_markup: InlineKeyboardMarkup) -> int:
    """Extract current page number from the message markup by finding the highlighted button."""
    if not reply_markup or not reply_markup.inline_keyboard:
        logger.debug("No reply markup or inline keyboard found, returning default page 0")
        return 0

    # Get the pagination row (last row)
    pagination_row = reply_markup.inline_keyboard[-1]
    logger.debug(f"Extracting current page from pagination row with {len(pagination_row)} buttons")

    # Find the button that's highlighted with dashes (current page)
    for button in pagination_row:
        if button.text.startswith("-") and button.text.endswith("-"):
            page = int(button.text.strip("-")) - 1  # Convert to 0-based
            logger.debug(f"Found current page: {page} from button text: '{button.text}'")
            return page

    logger.debug("No highlighted page button found, returning default page 0")
    return 0  # Default to first page if not found


def create_pagination_buttons(
    current_page: int, total_pages: int, callback_prefix: str
) -> list[InlineKeyboardButton]:
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
    logger.debug(
        f"Creating pagination buttons: current_page={current_page}, total_pages={total_pages}, prefix='{callback_prefix}'"
    )

    buttons = []
    if total_pages <= 1:
        logger.debug("Only one page available, creating simple pagination")
        buttons.append(InlineKeyboardButton("-1-", callback_data="noop"))
        return buttons

    if current_page == 0:
        logger.debug("On first page, highlighting page 1")
        buttons.append(InlineKeyboardButton("-1-", callback_data="noop"))
    else:
        logger.debug("Adding button for first page")
        buttons.append(InlineKeyboardButton("1", callback_data=f"{callback_prefix}:0"))

    if current_page > 2:
        logger.debug("Adding ellipsis for pages before current page region")
        buttons.append(InlineKeyboardButton("...", callback_data="noop"))

    # Add nearby pages
    for page in range(max(1, current_page - 1), min(total_pages - 1, current_page + 2)):
        if page == 0 or page == total_pages - 1:
            continue

        button_text = f"-{page + 1}-" if page == current_page else str(page + 1)
        callback_data = "noop" if page == current_page else f"{callback_prefix}:{page}"

        if page == current_page:
            logger.debug(f"Adding highlighted current page button for page {page + 1}")
        else:
            logger.debug(f"Adding button for page {page + 1}")

        buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))

    if current_page < total_pages - 3:
        logger.debug("Adding ellipsis for pages after current page region")
        buttons.append(InlineKeyboardButton("...", callback_data="noop"))

    # Add last page button
    if total_pages > 1:
        if current_page == total_pages - 1:
            logger.debug(f"On last page, highlighting page {total_pages}")
            buttons.append(InlineKeyboardButton(f"-{total_pages}-", callback_data="noop"))
        else:
            logger.debug(f"Adding button for last page {total_pages}")
            buttons.append(
                InlineKeyboardButton(
                    str(total_pages), callback_data=f"{callback_prefix}:{total_pages - 1}"
                )
            )

    logger.debug(f"Created {len(buttons)} pagination buttons")
    return buttons
