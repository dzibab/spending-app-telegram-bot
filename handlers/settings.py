"""Settings module for the spending tracker bot.

This module imports and re-exports handlers from the settings package
to maintain backward compatibility while using a more modular structure internally.
"""

# Re-export all the settings handlers from the modular structure
from handlers.settings import (
    settings_handler,
    handle_settings_callback,
    handle_settings_action,
    handle_add_currency,
    handle_remove_currency,
    handle_confirm_remove_currency,
    handle_set_main_currency,
    handle_add_category,
    handle_remove_category,
    handle_custom_input_request,
    handle_settings_text_input,
)
