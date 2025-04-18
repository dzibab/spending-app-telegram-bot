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


async def suggest_category_from_description(user_id: int, description: str, db) -> str:
    """Suggest a category based on the spending description.

    This function uses both keyword matching and the user's spending history
    to suggest the most appropriate category for a given description.

    Args:
        user_id: The user ID
        description: The spending description
        db: Database instance

    Returns:
        Suggested category name or None if no suggestion
    """
    if not description:
        return None

    # Convert to lowercase for case-insensitive matching
    description = description.lower()

    # Common keywords for different categories
    category_keywords = {
        "Food": [
            "food",
            "grocery",
            "groceries",
            "restaurant",
            "lunch",
            "dinner",
            "breakfast",
            "cafe",
            "coffee",
            "takeout",
            "meal",
            "snack",
            "supermarket",
        ],
        "Transport": [
            "transport",
            "uber",
            "taxi",
            "bus",
            "train",
            "subway",
            "metro",
            "gas",
            "fuel",
            "car",
            "ride",
            "lyft",
            "fare",
            "ticket",
            "transit",
        ],
        "Housing": ["rent", "mortgage", "apartment", "house", "housing", "maintenance", "repair"],
        "Utilities": [
            "utility",
            "utilities",
            "water",
            "electricity",
            "power",
            "bill",
            "phone",
            "internet",
            "cable",
            "gas",
            "heating",
        ],
        "Health": [
            "health",
            "doctor",
            "medical",
            "medicine",
            "pharmacy",
            "hospital",
            "dentist",
            "healthcare",
            "prescription",
            "clinic",
        ],
        "Entertainment": [
            "entertainment",
            "movie",
            "concert",
            "show",
            "game",
            "subscription",
            "netflix",
            "spotify",
            "ticket",
            "theme park",
            "streaming",
        ],
        "Shopping": [
            "shopping",
            "clothes",
            "clothing",
            "electronics",
            "furniture",
            "amazon",
            "store",
            "retail",
            "purchase",
            "buy",
        ],
        "Travel": [
            "travel",
            "hotel",
            "flight",
            "vacation",
            "trip",
            "booking",
            "airbnb",
            "airline",
            "holiday",
            "tour",
        ],
    }

    # Check for keyword matches
    best_matches = []
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in description:
                best_matches.append(category)
                break

    # If we have keyword matches, return the first one
    # (in the future we could prioritize based on frequency)
    if best_matches:
        # Get user categories to make sure the suggested one is available
        try:
            user_categories = await db.get_user_categories(user_id)
            for match in best_matches:
                if match in user_categories:
                    return match
        except Exception:
            # If there's any error, just return the first match
            return best_matches[0]

    # If no keyword matches, try to use user's spending history
    try:
        # Find previous spendings with similar descriptions
        query = """
            SELECT category, COUNT(*) as count
            FROM spendings
            WHERE user_id = ? AND description LIKE ?
            GROUP BY category
            ORDER BY count DESC
            LIMIT 1
        """

        # Use first word of description for rough matching
        first_word = description.split()[0] if description.split() else description
        search_pattern = f"%{first_word}%"

        # Execute the query
        async with db.connection() as cursor:
            await cursor.execute(query, (user_id, search_pattern))
            result = await cursor.fetchone()

            if result:
                return result[0]  # Return the most frequent category for similar descriptions
    except Exception:
        pass  # Ignore any errors in history lookup

    return None  # No suggestion found
