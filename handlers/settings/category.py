"""Category management functionality for settings."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action
from handlers.settings.utils import create_back_button, create_error_keyboard, get_common_categories


async def show_add_category_options(update: Update, user_id: int) -> None:
    """Show common categories that can be added."""
    query = update.callback_query
    log_user_action(user_id, "viewing add category options")

    try:
        # Get user's existing categories
        user_categories = await db.get_user_categories(user_id)

        # Filter out categories the user already has
        available_categories = [
            cat for cat in get_common_categories() if cat not in user_categories
        ]

        if not available_categories:
            # If all common categories are added, show custom input option
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Add Custom Category", callback_data="settings_custom:add_category"
                    )
                ],
                [create_back_button("settings_section:category")],
            ]
            await query.edit_message_text(
                "You've already added all common categories.\nYou can still add a custom category:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Show available common categories as buttons (2 per row)
        keyboard = []
        for i in range(0, len(available_categories), 2):  # 2 buttons per row
            row = []
            for j in range(2):
                if i + j < len(available_categories):
                    category = available_categories[i + j]
                    row.append(
                        InlineKeyboardButton(
                            category, callback_data=f"settings_add_category:{category}"
                        )
                    )
            keyboard.append(row)

        # Add custom input and back buttons
        keyboard.append(
            [
                InlineKeyboardButton(
                    "➕ Add Custom Category", callback_data="settings_custom:add_category"
                )
            ]
        )
        keyboard.append([create_back_button("settings_section:category")])

        await query.edit_message_text(
            "Select a category to add, or choose 'Add Custom Category' for a custom one:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await handle_db_error(query, "fetching categories", e)
        await query.edit_message_text(
            f"❌ Error fetching categories: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:category"),
        )


async def show_remove_category_options(update: Update, user_id: int) -> None:
    """Show user's categories that can be removed."""
    query = update.callback_query
    log_user_action(user_id, "viewing remove category options")

    try:
        # Get user's categories
        categories = await db.get_user_categories(user_id)

        if not categories:
            # No categories to remove
            await query.edit_message_text(
                "You don't have any categories to remove.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_section:category")]]
                ),
            )
            return

        # Create keyboard with all user categories
        keyboard = []
        for category in categories:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        category, callback_data=f"settings_remove_category:{category}"
                    )
                ]
            )

        keyboard.append([create_back_button("settings_section:category")])

        await query.edit_message_text(
            "Select a category to remove:", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await handle_db_error(query, "fetching categories", e)
        await query.edit_message_text(
            f"❌ Error fetching categories: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:category"),
        )


async def handle_add_category(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle adding a category from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"adding category '{category}' from settings")

    try:
        success = await db.add_category_to_user(user_id, category)
        if success:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Add Another Category", callback_data="settings_action:add_category"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "« Back to Category Settings", callback_data="settings_section:category"
                    )
                ],
            ]
            await query.edit_message_text(
                f"✅ Category '{category}' has been successfully added!",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                "Failed to add category. It might already exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:add_category")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"adding category {category}", e)
        await query.edit_message_text(
            f"❌ Error adding category: {e}",
            reply_markup=create_error_keyboard("settings_action:add_category"),
        )


async def handle_remove_category(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle removing a category from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"removing category '{category}' from settings")

    try:
        success = await db.remove_category_from_user(user_id, category)
        if success:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Remove Another Category", callback_data="settings_action:remove_category"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "« Back to Category Settings", callback_data="settings_section:category"
                    )
                ],
            ]
            await query.edit_message_text(
                f"✅ Category '{category}' has been successfully removed!",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                "Failed to remove category. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:remove_category")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"removing category {category}", e)
        await query.edit_message_text(
            f"❌ Error removing category: {e}",
            reply_markup=create_error_keyboard("settings_action:remove_category"),
        )
