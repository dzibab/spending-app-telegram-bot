"""Settings modules for the spending tracker bot."""

from handlers.settings.category import handle_add_category, handle_toggle_category
from handlers.settings.currency import (
    handle_add_currency,
    handle_set_main_currency,
    handle_toggle_currency,
)
from handlers.settings.custom_input import handle_custom_input_request, handle_settings_text_input
from handlers.settings.data_deletion import (
    handle_final_confirmation,
    execute_data_deletion,
)
from handlers.settings.menu import (
    handle_settings_action,
    handle_settings_callback,
    settings_handler,
)

__all__ = [
    # Category settings
    "handle_add_category",
    "handle_toggle_category",
    # Currency settings
    "handle_add_currency",
    "handle_toggle_currency",
    "handle_set_main_currency",
    # Custom text input handler
    "handle_custom_input_request",
    "handle_settings_text_input",
    # Data deletion
    "handle_final_confirmation",
    "execute_data_deletion",
    # Main settings menu
    "handle_settings_action",
    "handle_settings_callback",
    "settings_handler",
]
