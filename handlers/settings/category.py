"""Category management functionality for settings."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action
from handlers.settings.utils import create_back_button, create_error_keyboard, get_common_categories
from utils.category_utils import (
    add_category_to_user,
    toggle_category_status,
)


async def show_add_category_options(update: Update, user_id: int) -> None:
    """Show common categories that can be added."""
    query = update.callback_query
    log_user_action(user_id, "viewing add category options")

    try:
        # Get user's existing categories
        user_categories = await db.get_user_categories(user_id, include_archived=True)

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

        # Show available common categories as buttons
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
            "Select a category to add, or choose 'Add Custom Category' to enter a custom name:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        await handle_db_error(query, "fetching categories", e)
        await query.edit_message_text(
            f"❌ Error fetching categories: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:category"),
        )


async def show_manage_categories(update: Update, user_id: int) -> None:
    """Show unified interface for managing active and inactive categories."""
    query = update.callback_query
    log_user_action(user_id, "viewing category management")

    try:
        # Get user's active and archived categories
        active_categories = await db.get_user_categories(user_id)
        archived_categories = await db.get_archived_categories(user_id)

        if not active_categories and not archived_categories:
            # No categories to manage
            await query.edit_message_text(
                "You don't have any categories to manage. Add some categories first.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_section:category")]]
                ),
            )
            return

        # Create keyboard with all categories
        keyboard = []

        if active_categories:
            # Header for active section
            keyboard.append([InlineKeyboardButton("✅ ACTIVE CATEGORIES", callback_data="ignore")])

            for category in sorted(active_categories):
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            category, callback_data=f"settings_toggle_category:{category}"
                        )
                    ]
                )

        if archived_categories:
            # Add spacer if both active and archived exist
            if active_categories:
                keyboard.append([InlineKeyboardButton("─────────────", callback_data="ignore")])

            # Header for inactive section
            keyboard.append(
                [InlineKeyboardButton("❌ INACTIVE CATEGORIES", callback_data="ignore")]
            )

            for category in sorted(archived_categories):
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            category, callback_data=f"settings_toggle_category:{category}"
                        )
                    ]
                )

        keyboard.append([create_back_button("settings_section:category")])

        await query.edit_message_text(
            "Manage your categories:\n\n"
            "• Click on a category to toggle between active and inactive\n"
            "• Active categories can be used when adding spendings\n"
            "• Inactive categories still appear in reports but are hidden from selection menus",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
    log_user_action(user_id, f"adding category {category} from settings")

    try:
        success, message = await add_category_to_user(user_id, category)
        if success:
            # Show success message with options to add more or go back
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
                f"✅ {message}",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                f"❌ {message}",
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


async def handle_toggle_category(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle toggling a category's active state."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"toggling category status for '{category}'")

    try:
        # Use shared business logic to toggle the status
        success, message, is_active = await toggle_category_status(user_id, category)

        if success:
            # Return to the category management view
            await show_manage_categories(update, user_id)
        else:
            await query.edit_message_text(
                f"❌ {message}",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:manage_categories")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"toggling category {category}", e)
        await query.edit_message_text(
            f"❌ Error toggling category status: {e}",
            reply_markup=create_error_keyboard("settings_action:manage_categories"),
        )
