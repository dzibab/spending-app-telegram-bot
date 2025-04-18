"""Main settings menu handler for the spending tracker bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.common import log_user_action


async def settings_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /settings command - displays a menu of less frequently used commands."""
    user_id = update.effective_user.id
    log_user_action(user_id, "accessed settings menu")

    # Create the settings menu with grouped options
    keyboard = [
        # Currency Settings Group
        [InlineKeyboardButton("💱 Currency Settings", callback_data="settings_section:currency")],
        # Category Settings Group
        [InlineKeyboardButton("📋 Category Settings", callback_data="settings_section:category")],
        # Data Management Group
        [InlineKeyboardButton("📊 Data Management", callback_data="settings_section:data")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ *Settings Menu*\n\nSelect a settings category below:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_settings_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    data = query.data.split(":")
    section = data[1] if len(data) > 1 else None

    if section == "currency":
        await show_currency_section(update, _)

    elif section == "category":
        await show_category_section(update, _)

    elif section == "data":
        log_user_action(user_id, "accessed data management settings")
        keyboard = [
            [InlineKeyboardButton("📤 Export Spendings", callback_data="settings_action:export")],
            [InlineKeyboardButton("📥 Import Spendings", callback_data="settings_action:import")],
            [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
        ]
        text = "📊 *Data Management*\n\nImport or export your spending data:"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    else:
        # Return to main settings menu
        log_user_action(user_id, "returned to main settings menu")
        # Create the main settings menu with grouped options
        keyboard = [
            # Currency Settings Group
            [
                InlineKeyboardButton(
                    "💱 Currency Settings", callback_data="settings_section:currency"
                )
            ],
            # Category Settings Group
            [
                InlineKeyboardButton(
                    "📋 Category Settings", callback_data="settings_section:category"
                )
            ],
            # Data Management Group
            [InlineKeyboardButton("📊 Data Management", callback_data="settings_section:data")],
        ]
        text = "⚙️ *Settings Menu*\n\nSelect a settings category below:"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")


async def handle_settings_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings actions like add/remove currency/category."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else None

    # Import these here to avoid circular imports
    from handlers.settings.category import (
        show_add_category_options,
        show_archived_category_options,
        show_remove_category_options,
    )
    from handlers.settings.currency import (
        show_add_currency_options,
        show_archived_currency_options,
        show_main_currency_options,
        show_remove_currency_options,
    )

    match action:
        case "add_currency":
            # Show common currencies to add
            await show_add_currency_options(update, user_id)

        case "remove_currency":
            # Show user currencies to archive
            await show_remove_currency_options(update, user_id)

        case "restore_currency":
            # Show archived currencies to restore
            await show_archived_currency_options(update, user_id)

        case "main_currency":
            # Show currency selection for setting main currency
            await show_main_currency_options(update, user_id)

        case "add_category":
            # Show common categories to add
            await show_add_category_options(update, user_id)

        case "remove_category":
            # Show user categories to archive
            await show_remove_category_options(update, user_id)

        case "restore_category":
            # Show archived categories to restore
            await show_archived_category_options(update, user_id)

        case "export":
            # Use the new interactive export handler
            log_user_action(user_id, "starting interactive export from settings")
            # Show export range options
            keyboard = []
            from handlers.export_csv import EXPORT_RANGES

            for key, label in EXPORT_RANGES.items():
                keyboard.append([InlineKeyboardButton(label, callback_data=f"export_range:{key}")])

            # Add back button
            keyboard.append([InlineKeyboardButton("« Back", callback_data="settings_section:data")])

            await query.edit_message_text(
                "📤 *Export Your Spending Data*\n\nSelect a time range to export:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        case "import":
            # Use the interactive import handler directly in the current message
            log_user_action(user_id, "starting interactive import from settings")

            # Store that this import was initiated from settings
            context.user_data["import_from_settings"] = True

            # Show import instructions with template download option
            keyboard = [
                [InlineKeyboardButton("📝 Download Template", callback_data="import_template")],
                [InlineKeyboardButton("« Back to Settings", callback_data="import_cancel")],
            ]

            await query.edit_message_text(
                "📥 *Import Your Spending Data*\n\n"
                "To import your spendings, please upload a CSV file with the following columns:\n\n"
                "- *Date*: Required (formats: YYYY-MM-DD, DD-MM-YYYY with delimiters -, / or .)\n"
                "- *Amount*: Required (numeric value)\n"
                "- *Currency*: Required (3-letter currency code)\n"
                "- *Category*: Required\n"
                "- *Description*: Optional\n\n"
                "Simply upload your CSV file and I'll process it.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )


async def show_currency_section(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show currency settings section."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    log_user_action(user_id, "viewing currency settings")

    # Create keyboard with currency options
    keyboard = [
        [InlineKeyboardButton("➕ Add Currency", callback_data="settings_action:add_currency")],
        [
            InlineKeyboardButton(
                "🗄️ Archive Currency", callback_data="settings_action:remove_currency"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Restore Currency", callback_data="settings_action:restore_currency"
            )
        ],
        [
            InlineKeyboardButton(
                "🏆 Set Main Currency", callback_data="settings_action:main_currency"
            )
        ],
        [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
    ]

    await query.edit_message_text(
        "📊 *Currency Settings*\n\nManage your currencies:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def show_category_section(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show category settings section."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    log_user_action(user_id, "viewing category settings")

    # Create keyboard with category options
    keyboard = [
        [InlineKeyboardButton("➕ Add Category", callback_data="settings_action:add_category")],
        [
            InlineKeyboardButton(
                "🗄️ Archive Category", callback_data="settings_action:remove_category"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Restore Category", callback_data="settings_action:restore_category"
            )
        ],
        [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
    ]

    await query.edit_message_text(
        "📊 *Category Settings*\n\nManage your spending categories:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
