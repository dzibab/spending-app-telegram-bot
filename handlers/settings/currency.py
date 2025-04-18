"""Currency management functionality for settings."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action
from handlers.settings.utils import create_back_button, create_error_keyboard, get_common_currencies
from utils.logging import logger


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
                [InlineKeyboardButton(label, callback_data=f"settings_remove_currency:{currency}")]
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
        success = await db.add_currency_to_user(user_id, currency)
        if success:
            # If this is the first currency, also set it as main
            currencies = await db.get_user_currencies(user_id)
            if len(currencies) == 1:
                await db.set_user_main_currency(user_id, currency)
                message = f"Currency {currency} has been added and set as your main currency!"
            else:
                message = f"Currency {currency} has been successfully added!"

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
                "Failed to add currency. It might already exist or there was an error.",
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


async def handle_remove_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle archiving a currency from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"archiving currency {currency} from settings")

    try:
        # Check if currency is set as main currency
        current_main = await db.get_user_main_currency(user_id)
        if current_main == currency:
            # Confirm archiving of main currency
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Yes, Archive", callback_data=f"settings_confirm_remove_currency:{currency}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "No, Cancel", callback_data="settings_action:remove_currency"
                    )
                ],
            ]
            await query.edit_message_text(
                f"⚠️ {currency} is your main currency. Are you sure you want to archive it?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Otherwise proceed with archiving
        await process_currency_removal(update, user_id, currency)
    except Exception as e:
        await handle_db_error(query, f"archiving currency {currency}", e)
        await query.edit_message_text(
            f"❌ Error archiving currency: {e}",
            reply_markup=create_error_keyboard("settings_action:remove_currency"),
        )


async def handle_confirm_remove_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle confirmation for archiving a main currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"confirmed archiving of main currency {currency}")

    await process_currency_removal(update, user_id, currency)


async def handle_restore_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle restoring an archived currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"restoring archived currency {currency}")

    try:
        success = await db.unarchive_currency(user_id, currency)
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
                f"✅ Currency {currency} has been successfully restored!",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text(
                "Failed to restore currency. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:restore_currency")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"restoring currency {currency}", e)
        await query.edit_message_text(
            f"❌ Error restoring currency: {e}",
            reply_markup=create_error_keyboard("settings_action:restore_currency"),
        )


async def process_currency_removal(update: Update, user_id: int, currency: str) -> None:
    """Process the actual archiving of a currency."""
    query = update.callback_query

    try:
        # Check if currency is set as main currency
        current_main = await db.get_user_main_currency(user_id)
        if current_main == currency:
            # Remove from main_currency table
            await db.remove_user_main_currency(user_id)
            log_user_action(user_id, f"removed main currency {currency}")

            # Try to set another currency as main if available
            currencies = await db.get_user_currencies(user_id)
            currencies = [c for c in currencies if c != currency]
            if currencies:
                await db.set_user_main_currency(user_id, currencies[0])
                log_user_action(user_id, f"automatically set {currencies[0]} as new main currency")

        # Archive the currency instead of removing it
        success = await db.archive_currency(user_id, currency)
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

            # Customize message based on whether it was a main currency
            if current_main == currency:
                message = f"✅ Currency {currency} has been archived."
                if await db.get_user_main_currency(user_id):
                    new_main = await db.get_user_main_currency(user_id)
                    message += f"\n\n{new_main} has been set as your new main currency."
            else:
                message = f"✅ Currency {currency} has been successfully archived!"

            message += "\n\nThe currency will still be available for historical data and reports, but won't appear in selection menus."

            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(
                "Failed to archive currency. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[create_back_button("settings_action:remove_currency")]]
                ),
            )
    except Exception as e:
        logger.error(f"Error processing currency archival: {e}")
        await query.edit_message_text(
            f"❌ Error archiving currency: {e}",
            reply_markup=create_error_keyboard("settings_action:remove_currency"),
        )


async def handle_set_main_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle setting a main currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"setting main currency to {currency}")

    try:
        await db.set_user_main_currency(user_id, currency)

        keyboard = [
            [
                InlineKeyboardButton(
                    "« Back to Currency Settings", callback_data="settings_section:currency"
                )
            ]
        ]
        await query.edit_message_text(
            f"✅ Main currency set to {currency}", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await handle_db_error(query, f"setting main currency to {currency}", e)
        await query.edit_message_text(
            f"❌ Error setting main currency: {e}",
            reply_markup=create_error_keyboard("settings_action:main_currency"),
        )
