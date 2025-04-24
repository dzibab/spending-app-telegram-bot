"""Utilities for user management."""

from typing import Tuple

from db import db
from handlers.common import log_user_action
from utils.logging import logger


async def delete_all_user_data(user_id: int) -> Tuple[bool, str]:
    """Delete all data associated with a user.

    This is a destructive operation that removes all of the user's:
    - Spendings
    - Categories
    - Currencies
    - Settings

    Args:
        user_id: The Telegram user ID whose data should be deleted

    Returns:
        Tuple containing (success, message)
    """
    logger.warning(f"User {user_id} has requested complete data deletion")
    try:
        success = await db.delete_all_user_data(user_id)
        if success:
            logger.warning(f"Successfully deleted all data for user {user_id}")
            log_user_action(user_id, "deleted all personal data")
            return (
                True,
                "All your data has been successfully deleted. Default settings will be restored the next time you use the bot.",
            )
        else:
            logger.error(f"Failed to delete all data for user {user_id}")
            return False, "Failed to delete your data. Please try again later."
    except Exception as e:
        logger.error(f"Error deleting data for user {user_id}: {e}")
        return False, f"An error occurred: {e}"
