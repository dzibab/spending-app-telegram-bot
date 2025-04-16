from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import db
from utils.logging import logger


def truncate_text(text: Optional[str], max_length: int = 30) -> str:
    """Truncate text and add ellipsis if it exceeds max_length."""
    if not text:
        return ""
    return f"{text[:max_length]}..." if len(text) > max_length else text


async def list_spendings_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested a list of spendings.")

    # Show first page by default
    await show_spendings_page(update, user_id, page=0)


async def show_spendings_page(update: Update, user_id: int, page: int = 0):
    """Show a page of spendings with navigation buttons."""
    ITEMS_PER_PAGE = 10
    MAX_DESC_LENGTH = 30  # Maximum length for description before truncation
    offset = page * ITEMS_PER_PAGE

    # Get total count for pagination
    total_count = db.get_spendings_count(user_id)
    if total_count == 0:
        logger.info(f"No spendings found for user {user_id}.")
        await update.message.reply_text("📭 No spendings found.")
        return

    # Get paginated data
    rows = db.get_paginated_spendings(user_id, offset, ITEMS_PER_PAGE)
    total_pages = (total_count - 1) // ITEMS_PER_PAGE + 1

    # Calculate maximum widths for each column
    date_width = max(len(row[5]) for row in rows)
    amount_width = max(len(f"{row[2]:.2f}") for row in rows)
    currency_width = max(len(row[3]) for row in rows)
    category_width = max(len(row[4]) for row in rows)

    # Create header
    header = f"💸 Your spendings (Page {page + 1}/{total_pages}):\n\n"

    # Create message text with aligned columns and truncated descriptions
    message_lines = []
    for spending_id, desc, amount, currency, cat, dt in rows:
        # Format each field with fixed width
        date_part = f"{dt:<{date_width}}"
        amount_part = f"{amount:>{amount_width}.2f}"
        currency_part = f"{currency:<{currency_width}}"
        category_part = f"{cat:<{category_width}}"
        desc_part = truncate_text(desc, MAX_DESC_LENGTH)

        # Combine all parts with proper spacing and wrap in single backticks
        line = f"{date_part} | {amount_part} {currency_part} | {category_part}"
        if desc_part:
            line += f" | {desc_part}"
        message_lines.append(f"`{line}`")

    text = header + "\n".join(message_lines)

    # Create navigation buttons
    buttons = []
    if page > 0:  # Previous page
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list:{page-1}"))
    if page < total_pages - 1:  # Next page
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"list:{page+1}"))

    keyboard = [buttons] if buttons else None
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def handle_list_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handle pagination button presses."""
    query = update.callback_query
    user_id = query.from_user.id
    page = int(query.data.split(":")[1])

    await show_spendings_page(update, user_id, page)
