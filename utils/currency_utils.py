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
    try:
        # Check if currency already exists for this user
        existing_currencies = await db.get_user_currencies(user_id)
        if currency_code in existing_currencies:
            return False, f"You already have {currency_code} in your currencies."

        success = await db.add_currency_to_user(user_id, currency_code)
        if success:
            log_user_action(user_id, f"added currency {currency_code}")

            # Check if this is the first currency and set as main if so
            currencies = await db.get_user_currencies(user_id)
            if len(currencies) == 1:
                await db.set_user_main_currency(user_id, currency_code)
                return (
                    True,
                    f"Currency {currency_code} has been added and set as your main currency!",
                )
            else:
                return True, f"Currency {currency_code} has been successfully added!"
        else:
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
    try:
        # Check if currency is set as main currency
        current_main = await db.get_user_main_currency(user_id)
        was_main = current_main == currency_code
        new_main = None

        if was_main:
            # Remove from main_currency table
            await db.remove_user_main_currency(user_id)
            log_user_action(user_id, f"removed main currency {currency_code}")

            # Try to set another currency as main if available
            currencies = await db.get_user_currencies(user_id)
            other_currencies = [c for c in currencies if c != currency_code]
            if other_currencies:
                new_main = other_currencies[0]
                await db.set_user_main_currency(user_id, new_main)
                log_user_action(user_id, f"automatically set {new_main} as new main currency")

        # Remove or archive the currency
        if archive:
            success = await db.archive_currency(user_id, currency_code)
            action = "archived"
        else:
            success = await db.remove_currency_from_user(user_id, currency_code)
            action = "removed"

        if success:
            message = f"Currency {currency_code} has been {action}."

            if was_main and new_main:
                message += f"\n\n{new_main} has been set as your new main currency."

            if archive:
                message += "\n\nThe currency will still be available for historical data and reports, but won't appear in selection menus."

            return True, message, was_main
        else:
            return (
                False,
                f"Failed to {action} currency. It might not exist or there was an error.",
                was_main,
            )

    except Exception as e:
        logger.error(f"Error removing currency {currency_code} for user {user_id}: {e}")
        return False, f"Error removing currency: {e}", False


async def restore_archived_currency(user_id: int, currency_code: str) -> Tuple[bool, str]:
    """Restore an archived currency.

    Returns:
        Tuple containing (success, message)
    """
    try:
        success = await db.unarchive_currency(user_id, currency_code)
        if success:
            log_user_action(user_id, f"restored archived currency {currency_code}")
            return True, f"Currency {currency_code} has been successfully restored!"
        else:
            return False, "Failed to restore currency. It might not exist or there was an error."
    except Exception as e:
        logger.error(f"Error restoring currency {currency_code} for user {user_id}: {e}")
        return False, f"Error restoring currency: {e}"


async def set_main_currency(user_id: int, currency_code: str) -> Tuple[bool, str]:
    """Set a currency as the main currency.

    Returns:
        Tuple containing (success, message)
    """
    try:
        await db.set_user_main_currency(user_id, currency_code)
        log_user_action(user_id, f"set main currency to {currency_code}")
        return True, f"Main currency set to {currency_code}"
    except Exception as e:
        logger.error(f"Error setting main currency {currency_code} for user {user_id}: {e}")
        return False, f"Error setting main currency: {e}"
