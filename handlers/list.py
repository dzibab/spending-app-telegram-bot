from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from constants import ITEMS_PER_PAGE
from db import db
from handlers.common import log_user_action
from utils.pagination import (
    create_pagination_buttons,
    get_current_page_from_markup,
)
from utils.spending_actions import handle_delete_spending
from utils.ui_helpers import (
    format_spending_button_text,
    format_spending_details,
    handle_no_results,
)


async def show_spendings_page(update: Update, user_id: int, page: int = 0):
    """Show a page of spendings with navigation buttons."""
    offset = page * ITEMS_PER_PAGE
    log_user_action(user_id, f"viewing spendings list page {page + 1}")

    # Get total count for pagination
    total_count = await db.get_spendings_count(user_id)
    if total_count == 0:
        log_user_action(user_id, "attempted to view list but has no spendings")
        await handle_no_results(update, "No spendings found")
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
    for spending in rows:
        # Access fields as properties of the Spending object
        spending_id = spending.id
        button_text = format_spending_button_text(spending)
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"list_detail:{spending_id}")]
        )

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
    log_user_action(user_id, "requested a list of spendings")
    await show_spendings_page(update, user_id)


async def handle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        log_user_action(user_id, f"viewing detail of spending {spending_id}")

        # Get the current page by finding the highlighted button in pagination
        current_page = get_current_page_from_markup(query.message.reply_markup)

        spending = await db.get_spending_by_id(user_id, spending_id)

        if spending:
            # Show detailed view with back and delete buttons
            text = await format_spending_details(spending)
            # Add both back and delete buttons
            keyboard = [
                [InlineKeyboardButton("« Back to list", callback_data=f"list_page:{current_page}")],
                [
                    InlineKeyboardButton(
                        "🗑️ Delete", callback_data=f"list_delete:{spending_id}:{current_page}"
                    )
                ],
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("❌ Spending not found.")
    elif data.startswith("list_delete:"):
        # Handle deletion of spending from detail view
        parts = data.split(":")
        spending_id = int(parts[1])
        current_page = int(parts[2])
        log_user_action(user_id, f"deleting spending {spending_id} from list")

        # Use the common deletion handler
        await handle_delete_spending(
            update=update,
            context=context,
            user_id=user_id,
            spending_id=spending_id,
            current_page=current_page,
            return_callback_prefix="list_page",
            get_item_count_fn=db.get_spendings_count,
            show_results_fn=show_spendings_page,
        )
