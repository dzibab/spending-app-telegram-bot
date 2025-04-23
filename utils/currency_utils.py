"""Currency-related business logic utilities shared across different handlers."""

from typing import Tuple

from telegram import Update

from db import db
from handlers.common import log_user_action
from utils.logging import logger


async def add_currency_to_user(user_id: int, currency_code: str) -> Tuple[bool, str]:
    """Add currency to a user's account.

    Returns:
        Tuple containing (success, message)
    """
    logger.info(f"Attempting to add currency {currency_code} for user {user_id}")
    try:
        # Check if currency already exists for this user
        existing_currencies = await db.get_user_currencies(user_id)
        if currency_code in existing_currencies:
            logger.info(f"Currency {currency_code} already exists for user {user_id}")
            return False, f"You already have {currency_code} in your currencies."

        success = await db.add_currency_to_user(user_id, currency_code)
        if success:
            log_user_action(user_id, f"added currency {currency_code}")
            logger.info(f"Successfully added currency {currency_code} for user {user_id}")

            # Check if this is the first currency and set as main if so
            currencies = await db.get_user_currencies(user_id)
            if len(currencies) == 1:
                logger.info(
                    f"Setting {currency_code} as main currency (first currency) for user {user_id}"
                )
                await db.set_user_main_currency(user_id, currency_code)
                return (
                    True,
                    f"Currency {currency_code} has been added and set as your main currency!",
                )
            else:
                return True, f"Currency {currency_code} has been successfully added!"
        else:
            logger.warning(f"Failed to add currency {currency_code} for user {user_id}")
            return False, "Failed to add currency. It might already exist or there was an error."
    except Exception as e:
        logger.error(f"Error adding currency {currency_code} for user {user_id}: {e}")
        return False, f"Error adding currency: {e}"


async def remove_currency(
    user_id: int, currency_code: str, archive: bool = True
) -> Tuple[bool, str, bool]:
    """Remove or archive a currency from a user's account.

    Args:
        user_id: The Telegram user ID
        currency_code: The currency code to remove
        archive: Whether to archive (True) or completely remove (False) the currency

    Returns:
        Tuple containing (success, message, was_main_currency)
    """
    action_type = "archiving" if archive else "removing"
    logger.info(f"Attempting {action_type} currency {currency_code} for user {user_id}")
    try:
        # Check if currency is set as main currency
        current_main = await db.get_user_main_currency(user_id)
        was_main = current_main == currency_code
        new_main = None

        if was_main:
            logger.info(
                f"Currency {currency_code} is the main currency for user {user_id}, removing main status"
            )
            # Remove from main_currency table
            await db.remove_user_main_currency(user_id)
            log_user_action(user_id, f"removed main currency {currency_code}")

            # Try to set another currency as main if available
            currencies = await db.get_user_currencies(user_id)
            other_currencies = [c for c in currencies if c != currency_code]
            logger.debug(f"Other available currencies for user {user_id}: {other_currencies}")

            if other_currencies:
                new_main = other_currencies[0]
                logger.info(f"Setting {new_main} as the new main currency for user {user_id}")
                await db.set_user_main_currency(user_id, new_main)
                log_user_action(user_id, f"automatically set {new_main} as new main currency")
            else:
                logger.info(f"No other currencies available for user {user_id} to set as main")

        # Remove or archive the currency
        if archive:
            logger.info(f"Archiving currency {currency_code} for user {user_id}")
            success = await db.archive_currency(user_id, currency_code)
            action = "archived"
        else:
            logger.info(f"Completely removing currency {currency_code} for user {user_id}")
            success = await db.remove_currency_from_user(user_id, currency_code)
            action = "removed"

        if success:
            logger.info(f"Successfully {action} currency {currency_code} for user {user_id}")
            message = f"Currency {currency_code} has been {action}."

            if was_main and new_main:
                message += f"\n\n{new_main} has been set as your new main currency."

            if archive:
                message += "\n\nThe currency will still be available for historical data and reports, but won't appear in selection menus."

            return True, message, was_main
        else:
            logger.warning(f"Failed to {action} currency {currency_code} for user {user_id}")
            return (
                False,
                f"Failed to {action} currency. It might not exist or there was an error.",
                was_main,
            )

    except Exception as e:
        logger.error(f"Error {action_type} currency {currency_code} for user {user_id}: {e}")
        return False, f"Error {action_type.replace('ing', '')} currency: {e}", False


async def restore_archived_currency(user_id: int, currency_code: str) -> Tuple[bool, str]:
    """Restore an archived currency.

    Returns:
        Tuple containing (success, message)
    """
    logger.info(f"Attempting to restore archived currency {currency_code} for user {user_id}")
    try:
        success = await db.unarchive_currency(user_id, currency_code)
        if success:
            logger.info(
                f"Successfully restored archived currency {currency_code} for user {user_id}"
            )
            log_user_action(user_id, f"restored archived currency {currency_code}")
            return True, f"Currency {currency_code} has been successfully restored!"
        else:
            logger.warning(f"Failed to restore currency {currency_code} for user {user_id}")
            return False, "Failed to restore currency. It might not exist or there was an error."
    except Exception as e:
        logger.error(f"Error restoring currency {currency_code} for user {user_id}: {e}")
        return False, f"Error restoring currency: {e}"


async def toggle_currency_status(user_id: int, currency_code: str) -> Tuple[bool, str, bool]:
    """Toggle the active status of a currency.

    If active, it will be deactivated.
    If inactive, it will be activated.

    Args:
        user_id: The user ID
        currency_code: The currency code to toggle

    Returns:
        Tuple containing (success, message, is_active_now)
    """
    logger.info(f"Toggling status for currency {currency_code} for user {user_id}")
    try:
        # Check current status
        is_archived = currency_code in await db.get_archived_currencies(user_id)
        logger.debug(f"Currency {currency_code} is_archived={is_archived} for user {user_id}")

        if is_archived:
            # Currency is archived, unarchive it (activate)
            logger.debug(f"Unarchiving currency {currency_code} for user {user_id}")
            success, message = await restore_archived_currency(user_id, currency_code)
            return success, message, True
        else:
            # Currency is active, archive it (deactivate)
            logger.debug(f"Archiving previously active currency {currency_code} for user {user_id}")
            success, message, was_main = await remove_currency(user_id, currency_code, archive=True)
            return success, message, False

    except Exception as e:
        logger.error(f"Error toggling currency {currency_code} status for user {user_id}: {e}")
        return False, f"Error toggling currency status: {e}", False


async def set_main_currency(user_id: int, currency_code: str) -> Tuple[bool, str]:
    """Set a currency as the main currency for a user.

    Returns:
        Tuple containing (success, message)
    """
    logger.info(f"Setting {currency_code} as main currency for user {user_id}")
    try:
        # Check if the currency exists for this user
        currencies = await db.get_user_currencies(user_id)
        if currency_code not in currencies:
            logger.warning(f"Currency {currency_code} not found in user {user_id}'s currencies")
            return False, f"Currency {currency_code} is not in your currencies."

        # Check if it's already the main currency
        current_main = await db.get_user_main_currency(user_id)
        if currency_code == current_main:
            logger.info(f"Currency {currency_code} is already the main currency for user {user_id}")
            return False, f"{currency_code} is already your main currency."

        logger.info(
            f"Changing main currency from {current_main or 'None'} to {currency_code} for user {user_id}"
        )
        await db.set_user_main_currency(user_id, currency_code)
        log_user_action(user_id, f"set main currency to {currency_code}")
        return True, f"{currency_code} has been set as your main currency!"

    except Exception as e:
        logger.error(f"Error setting main currency {currency_code} for user {user_id}: {e}")
        return False, f"Error setting main currency: {e}"
