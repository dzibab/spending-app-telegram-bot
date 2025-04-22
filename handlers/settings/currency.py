"""Currency management functionality for settings."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action
from handlers.settings.utils import create_back_button, create_error_keyboard, get_common_currencies
from utils.currency_utils import (
    add_currency_to_user,
    remove_currency,
    restore_archived_currency,
    set_main_currency,
)


async def show_add_currency_options(update: Update, user_id: int) -> None:
    """Show common currencies that can be added."""
    query = update.callback_query
    log_user_action(user_id, "viewing add currency options")

    try:
        # Get user's existing currencies (both active and archived)
        user_currencies = await db.get_user_currencies(user_id, include_archived=True)

        # Filter out currencies the user already has
        available_currencies = [
            curr for curr in get_common_currencies() if curr not in user_currencies
        ]

        if not available_currencies:
            # If all common currencies are added, show custom input option
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Add Custom Currency", callback_data="settings_custom:add_currency"
                    )
                ],
                [create_back_button("settings_section:currency")],
            ]
            await query.edit_message_text(
                "You've already added all common currencies.\nYou can still add a custom currency:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Show available common currencies as buttons
        keyboard = []
        for i in range(0, len(available_currencies), 3):  # 3 buttons per row
            row = []
            for j in range(3):
                if i + j < len(available_currencies):
                    currency = available_currencies[i + j]
                    row.append(
                        InlineKeyboardButton(
                            currency, callback_data=f"settings_add_currency:{currency}"
                        )
                    )
            keyboard.append(row)

        # Add custom input and back buttons
        keyboard.append(
            [
                InlineKeyboardButton(
                    "➕ Add Custom Currency", callback_data="settings_custom:add_currency"
                )
            ]
        )
        keyboard.append([create_back_button("settings_section:currency")])

        await query.edit_message_text(
            "Select a currency to add, or choose 'Add Custom Currency' to enter a custom code:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await handle_db_error(query, "fetching currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching currencies: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:currency"),
        )


async def show_remove_currency_options(update: Update, user_id: int) -> None:
    """Show user's currencies that can be archived."""
    query = update.callback_query
    log_user_action(user_id, "viewing archive currency options")

    try:
        # Get user's currencies and main currency
        currencies = await db.get_user_currencies(user_id)
        current_main = await db.get_user_main_currency(user_id)

        if not currencies:
            # No currencies to archive
            await query.edit_message_text(
                "You don't have any currencies to archive.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_section:currency")]]
                ),
            )
            return

        # Create keyboard with all user currencies
        keyboard = []
        for currency in currencies:
            # Mark main currency with a check mark
            label = f"{currency} {'✓' if currency == current_main else ''}"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        label, callback_data=f"settings_confirm_remove_currency:{currency}"
                    )
                ]
            )

        keyboard.append([create_back_button("settings_section:currency")])

        await query.edit_message_text(
            "Select a currency to archive:"
            + (
                "\n\n*Note: The currency marked with ✓ is your main currency*"
                if current_main
                else ""
            )
            + "\n\nArchived currencies will still be available for reports and historical data, but will be hidden from selection menus.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    except Exception as e:
        await handle_db_error(query, "fetching currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching currencies: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:currency"),
        )


async def show_main_currency_options(update: Update, user_id: int) -> None:
    """Show currency selection for setting main currency."""
    query = update.callback_query
    log_user_action(user_id, "viewing main currency options")

    try:
        # Get user's existing currencies
        currencies = await db.get_user_currencies(user_id)
        if not currencies:
            await query.edit_message_text(
                "You don't have any currencies yet. Please add currencies first.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Add Currency", callback_data="settings_action:add_currency"
                            ),
                            create_back_button("settings_section:currency"),
                        ]
                    ]
                ),
            )
            return

        # Get current main currency
        current_main = await db.get_user_main_currency(user_id)

        # Create keyboard with all user currencies
        keyboard = []
        for currency in currencies:
            label = f"{currency} {'✓' if currency == current_main else ''}"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        label, callback_data=f"settings_set_main_currency:{currency}"
                    )
                ]
            )

        # Add back button
        keyboard.append([create_back_button("settings_section:currency")])

        await query.edit_message_text(
            "Select your main currency:"
            + ("\n\n*Current main currency is marked with ✓*" if current_main else ""),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    except Exception as e:
        await handle_db_error(query, "fetching currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching currencies: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:currency"),
        )


async def show_archived_currency_options(update: Update, user_id: int) -> None:
    """Show user's archived currencies that can be restored."""
    query = update.callback_query
    log_user_action(user_id, "viewing archived currencies")

    try:
        # Get user's archived currencies
        archived_currencies = await db.get_archived_currencies(user_id)

        if not archived_currencies:
            # No archived currencies
            await query.edit_message_text(
                "You don't have any archived currencies to restore.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_section:currency")]]
                ),
            )
            return

        # Create keyboard with all archived currencies
        keyboard = []
        for currency in archived_currencies:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        currency, callback_data=f"settings_restore_currency:{currency}"
                    )
                ]
            )

        keyboard.append([create_back_button("settings_section:currency")])

        await query.edit_message_text(
            "Select a currency to restore:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await handle_db_error(query, "fetching archived currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching archived currencies: {e}\n\nPlease try again later.",
            reply_markup=create_error_keyboard("settings_section:currency"),
        )


async def handle_add_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle adding a currency from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"adding currency {currency} from settings")

    try:
        # Use the shared business logic utility
        success, message = await add_currency_to_user(user_id, currency)

        if success:
            # Show success message with options to add more or go back
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Add Another Currency", callback_data="settings_action:add_currency"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "« Back to Currency Settings", callback_data="settings_section:currency"
                    )
                ],
            ]
            await query.edit_message_text(
                f"✅ {message}", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                f"❌ {message}",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:add_currency")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"adding currency {currency}", e)
        await query.edit_message_text(
            f"❌ Error adding currency: {e}",
            reply_markup=create_error_keyboard("settings_action:add_currency"),
        )


async def handle_confirm_remove_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle confirmation for archiving a currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"confirmed archiving currency {currency}")

    await process_currency_removal(update, user_id, currency)


async def handle_restore_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle restoring an archived currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"restoring archived currency {currency}")

    # Use shared business logic
    success, message = await restore_archived_currency(user_id, currency)

    if success:
        keyboard = [
            [
                InlineKeyboardButton(
                    "Restore Another", callback_data="settings_action:restore_currency"
                )
            ],
            [
                InlineKeyboardButton(
                    "« Back to Currency Settings", callback_data="settings_section:currency"
                )
            ],
        ]
        await query.edit_message_text(
            f"✅ {message}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=InlineKeyboardMarkup(
                [[create_back_button("settings_action:restore_currency")]]
            ),
        )


async def process_currency_removal(update: Update, user_id: int, currency: str) -> None:
    """Process the actual archiving of a currency."""
    query = update.callback_query

    # Use shared business logic (with archive=True as this is the settings method)
    success, message, was_main = await remove_currency(user_id, currency, archive=True)

    if success:
        keyboard = [
            [
                InlineKeyboardButton(
                    "Archive Another Currency", callback_data="settings_action:remove_currency"
                )
            ],
            [
                InlineKeyboardButton(
                    "« Back to Currency Settings", callback_data="settings_section:currency"
                )
            ],
        ]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(
                [[create_back_button("settings_action:remove_currency")]]
            ),
        )


async def handle_set_main_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle setting a main currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]

    # Use shared business logic
    success, message = await set_main_currency(user_id, currency)

    if success:
        keyboard = [
            [
                InlineKeyboardButton(
                    "« Back to Currency Settings", callback_data="settings_section:currency"
                )
            ]
        ]
        await query.edit_message_text(f"✅ {message}", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=create_error_keyboard("settings_action:main_currency"),
        )
