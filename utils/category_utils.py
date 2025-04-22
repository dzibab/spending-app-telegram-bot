"""Category-related business logic utilities shared across different handlers."""

from typing import Tuple

from db import db
from handlers.common import log_user_action
from utils.logging import logger


async def add_category_to_user(user_id: int, category_name: str) -> Tuple[bool, str]:
    """Add category to a user's account.

    Returns:
        Tuple containing (success, message)
    """
    try:
        # Check if category already exists for this user
        existing_categories = await db.get_user_categories(user_id)
        if category_name in existing_categories:
            return False, f"You already have '{category_name}' in your categories."

        success = await db.add_category_to_user(user_id, category_name)
        if success:
            log_user_action(user_id, f"added category '{category_name}'")
            return True, f"Category '{category_name}' has been successfully added!"
        else:
            return False, "Failed to add category. It might already exist or there was an error."
    except Exception as e:
        logger.error(f"Error adding category {category_name} for user {user_id}: {e}")
        return False, f"Error adding category: {e}"


async def archive_category(user_id: int, category_name: str) -> Tuple[bool, str]:
    """Archive a category from a user's account.

    Args:
        user_id: The Telegram user ID
        category_name: The category name to archive

    Returns:
        Tuple containing (success, message)
    """
    try:
        success = await db.archive_category(user_id, category_name)
        if success:
            log_user_action(user_id, f"archived category '{category_name}'")
            return True, f"Category '{category_name}' has been archived."
        else:
            return (
                False,
                f"Failed to archive category '{category_name}'. It might not exist or there was an error.",
            )
    except Exception as e:
        logger.error(f"Error archiving category {category_name} for user {user_id}: {e}")
        return False, f"Error archiving category: {e}"


async def restore_category(user_id: int, category_name: str) -> Tuple[bool, str]:
    """Restore an archived category.

    Returns:
        Tuple containing (success, message)
    """
    try:
        success = await db.unarchive_category(user_id, category_name)
        if success:
            log_user_action(user_id, f"restored archived category '{category_name}'")
            return True, f"Category '{category_name}' has been successfully restored!"
        else:
            return (
                False,
                f"Failed to restore category '{category_name}'. It might not exist or there was an error.",
            )
    except Exception as e:
        logger.error(f"Error restoring category {category_name} for user {user_id}: {e}")
        return False, f"Error restoring category: {e}"


async def toggle_category_status(user_id: int, category_name: str) -> Tuple[bool, str, bool]:
    """Toggle the active status of a category.

    If active, it will be deactivated (archived).
    If inactive, it will be activated (restored).

    Args:
        user_id: The user ID
        category_name: The category name to toggle

    Returns:
        Tuple containing (success, message, is_active_now)
    """
    try:
        # Check current status
        is_archived = category_name in await db.get_archived_categories(user_id)

        if is_archived:
            # Category is archived, unarchive it (activate)
            success, message = await restore_category(user_id, category_name)
            return success, message, True
        else:
            # Category is active, archive it (deactivate)
            success, message = await archive_category(user_id, category_name)
            return success, message, False

    except Exception as e:
        logger.error(f"Error toggling category {category_name} status for user {user_id}: {e}")
        return False, f"Error toggling category status: {e}", False
