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


async def show_remove_category_options(update: Update, user_id: int) -> None:
    """Show user's categories that can be archived."""
    query = update.callback_query
    log_user_action(user_id, "viewing archive category options")

    try:
        # Get user's categories
        categories = await db.get_user_categories(user_id)

        if not categories:
            # No categories to archive
            await query.edit_message_text(
                "You don't have any categories to archive.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_section:category")]]
                ),
            )
            return

        # Create keyboard with all user categories
        keyboard = []
        for category in sorted(categories):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        category, callback_data=f"settings_remove_category:{category}"
                    )
                ]
            )

        keyboard.append([create_back_button("settings_section:category")])

        await query.edit_message_text(
            "Select a category to archive:\n\nArchived categories will still be available for historical spendings and reports, but will be hidden from selection menus.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        await handle_db_error(query, "fetching categories", e)
        await query.edit_message_text(
            f"❌ Error fetching categories: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:category"),
        )


async def show_archived_category_options(update: Update, user_id: int) -> None:
    """Show user's archived categories that can be restored."""
    query = update.callback_query
    log_user_action(user_id, "viewing archived categories")

    try:
        # Get user's archived categories
        archived_categories = await db.get_archived_categories(user_id)

        if not archived_categories:
            # No archived categories
            await query.edit_message_text(
                "You don't have any archived categories to restore.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_section:category")]]
                ),
            )
            return

        # Create keyboard with all archived categories
        keyboard = []
        for category in sorted(archived_categories):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        category, callback_data=f"settings_restore_category:{category}"
                    )
                ]
            )

        keyboard.append([create_back_button("settings_section:category")])

        await query.edit_message_text(
            "Select a category to restore:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await handle_db_error(query, "fetching archived categories", e)
        await query.edit_message_text(
            f"❌ Error fetching archived categories: {e}\n\nPlease try again later.",
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
        success = await db.add_category_to_user(user_id, category)
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
                f"✅ Category '{category}' has been successfully added!",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                f"Failed to add category '{category}'. It might already exist or there was an error.",
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
    """Handle archiving a category from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"archiving category {category} from settings")

    try:
        # Archive the category instead of removing it
        success = await db.archive_category(user_id, category)
        if success:
            # Show success message with options to archive more or go back
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Archive Another Category", callback_data="settings_action:remove_category"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "« Back to Category Settings", callback_data="settings_section:category"
                    )
                ],
            ]
            await query.edit_message_text(
                f"✅ Category '{category}' has been archived.\n\nThe category will still be available for historical spendings and reports, but won't appear in selection menus.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                f"Failed to archive category '{category}'. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:remove_category")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"archiving category {category}", e)
        await query.edit_message_text(
            f"❌ Error archiving category: {e}",
            reply_markup=create_error_keyboard("settings_action:remove_category"),
        )


async def handle_restore_category(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle restoring an archived category."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"restoring archived category {category}")

    try:
        success = await db.unarchive_category(user_id, category)
        if success:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Restore Another", callback_data="settings_action:restore_category"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "« Back to Category Settings", callback_data="settings_section:category"
                    )
                ],
            ]
            await query.edit_message_text(
                f"✅ Category '{category}' has been successfully restored!",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                f"Failed to restore category '{category}'. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:restore_category")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"restoring category {category}", e)
        await query.edit_message_text(
            f"❌ Error restoring category: {e}",
            reply_markup=create_error_keyboard("settings_action:restore_category"),
        )
