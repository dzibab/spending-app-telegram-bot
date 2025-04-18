"""Spending-related business logic handlers."""

import inspect

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from constants import ITEMS_PER_PAGE
from db import db
from utils.logging import logger


async def handle_delete_spending(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    spending_id: int,
    current_page: int,
    return_callback_prefix: str,
    get_item_count_fn,
    show_results_fn,
    **kwargs,
) -> None:
    """Handle spending deletion logic common to both list and search views."""
    logger.info(f"User {user_id} deleting spending {spending_id}")
    success = await db.remove_spending(user_id, spending_id)
    if success:
        logger.info(f"Successfully removed spending {spending_id} for user {user_id}")
        total_count = await get_item_count_fn(user_id, **kwargs)
        items_on_current_page = total_count - (current_page * ITEMS_PER_PAGE)
        if items_on_current_page <= 0 and current_page > 0:
            current_page -= 1
        await update.callback_query.edit_message_text("✅ Spending deleted successfully!")
        sig = inspect.signature(show_results_fn)
        param_names = list(sig.parameters.keys())
        if len(param_names) >= 3 and param_names[2] == "page":
            await show_results_fn(update, user_id, page=current_page, **kwargs)
        else:
            if "page" not in kwargs:
                kwargs["page"] = current_page
            await show_results_fn(update, user_id, **kwargs)
    else:
        logger.warning(f"Failed to remove spending {spending_id} for user {user_id}")
        back_button = InlineKeyboardButton(
            "« Back", callback_data=f"{return_callback_prefix}:{current_page}"
        )
        await update.callback_query.edit_message_text(
            "❌ Failed to delete spending. It might have been already removed.",
            reply_markup=InlineKeyboardMarkup([[back_button]]),
        )
