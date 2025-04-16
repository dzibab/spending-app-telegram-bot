from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import db
from utils.logging import logger


async def show_spendings_page(update: Update, user_id: int, page: int = 0):
    """Show a page of spendings with navigation buttons."""
    ITEMS_PER_PAGE = 5  # Fewer items since each is a button
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
            callback_data=f"list_detail:{spending_id}"
        )])

    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_page:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"list_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

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
    if data.startswith("list_page:"):
        # Handle pagination
        page = int(data.split(":")[1])
        await show_spendings_page(update, user_id, page)
    elif data.startswith("list_detail:"):
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
            # Add a back button to return to the list
            keyboard = [[InlineKeyboardButton("« Back to list", callback_data="list_page:0")]]
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Spending not found.")
