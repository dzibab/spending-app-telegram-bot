"""Common utilities for handler functionality."""

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.logging import logger


async def cancel(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Common cancel function for conversation handlers."""
    await update.message.reply_text("Operation canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def create_keyboard_markup(items: list[str], one_time: bool = True, resize: bool = True) -> ReplyKeyboardMarkup:
    """Create a keyboard markup from a list of items.

    Args:
        items: List of strings to use as keyboard buttons
        one_time: Whether keyboard should hide after a selection
        resize: Whether keyboard should be resized to fit buttons

    Returns:
        ReplyKeyboardMarkup with one button per item
    """
    keyboard = [[item] for item in items]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=one_time, resize_keyboard=resize)


def log_user_action(user_id: int, action: str) -> None:
    """Log a user action with standardized format.

    Args:
        user_id: The user's Telegram ID
        action: Description of the action being performed
    """
    logger.info(f"User {user_id} {action}")


async def handle_db_error(update: Update, action: str, error: Exception) -> None:
    """Handle database errors with standardized responses.

    Args:
        update: Telegram update object
        action: Description of the action that failed
        error: The exception that was raised
    """
    logger.error(f"Error {action}: {error}")
    await update.message.reply_text(f"❌ Error {action}. Please try again.")
