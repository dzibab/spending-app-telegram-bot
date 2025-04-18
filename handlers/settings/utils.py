"""Utility functions and constants for settings modules."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Common currency codes to offer for quick addition
COMMON_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "HKD", "SGD"]

# Common spending categories to offer for quick addition
COMMON_CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Utilities",
    "Health",
    "Entertainment",
    "Shopping",
    "Travel",
    "Education",
    "Gifts",
    "Subscriptions",
    "Personal Care",
    "Pets",
]


def get_common_currencies():
    """Return list of common currencies."""
    return COMMON_CURRENCIES


def get_common_categories():
    """Return list of common categories."""
    return COMMON_CATEGORIES


def create_back_button(callback_data: str):
    """Create a standard back button."""
    return InlineKeyboardButton("« Back", callback_data=callback_data)


def create_error_keyboard(back_callback_data: str):
    """Create keyboard with just a back button for error scenarios."""
    return InlineKeyboardMarkup([[create_back_button(back_callback_data)]])
