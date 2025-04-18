"""Settings modules for the spending tracker bot."""

from handlers.settings.menu import (
    settings_handler,
    handle_settings_callback,
    handle_settings_action,
)
from handlers.settings.currency import (
    handle_add_currency,
    handle_remove_currency,
    handle_confirm_remove_currency,
    handle_set_main_currency,
)
from handlers.settings.category import handle_add_category, handle_remove_category
from handlers.settings.custom_input import handle_custom_input_request, handle_settings_text_input

__all__ = [
    # Main settings menu
    "settings_handler",
    "handle_settings_callback",
    "handle_settings_action",
    # Currency settings
    "handle_add_currency",
    "handle_remove_currency",
    "handle_confirm_remove_currency",
    "handle_set_main_currency",
    # Category settings
    "handle_add_category",
    "handle_remove_category",
    # Custom text input handler
    "handle_custom_input_request",
    "handle_settings_text_input",
]
