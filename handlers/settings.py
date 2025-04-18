"""Settings menu handler for the spending bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import handle_db_error, log_user_action
from utils.logging import logger

# A list of common currency codes to offer for quick addition
COMMON_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "HKD", "SGD"]
# A list of common spending categories to offer for quick addition
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
        "⚙️ *Settings Menu*\n\nSelect a settings category below:", reply_markup=reply_markup, parse_mode="Markdown"
    )


async def handle_settings_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    data = query.data.split(":")
    section = data[1] if len(data) > 1 else None

    if section == "currency":
        log_user_action(user_id, "accessed currency settings")
        keyboard = [
            [InlineKeyboardButton("➕ Add Currency", callback_data="settings_action:add_currency")],
            [InlineKeyboardButton("➖ Remove Currency", callback_data="settings_action:remove_currency")],
            [InlineKeyboardButton("🔄 Set Main Currency", callback_data="settings_action:main_currency")],
            [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
        ]
        text = "💱 *Currency Settings*\n\nManage your currencies:"

    elif section == "category":
        log_user_action(user_id, "accessed category settings")
        keyboard = [
            [InlineKeyboardButton("➕ Add Category", callback_data="settings_action:add_category")],
            [InlineKeyboardButton("➖ Remove Category", callback_data="settings_action:remove_category")],
            [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
        ]
        text = "📋 *Category Settings*\n\nManage your spending categories:"

    elif section == "data":
        log_user_action(user_id, "accessed data management settings")
        keyboard = [
            [InlineKeyboardButton("📤 Export Spendings", callback_data="settings_action:export")],
            [InlineKeyboardButton("📥 Import Spendings", callback_data="settings_action:import")],
            [InlineKeyboardButton("« Back", callback_data="settings_back:main")],
        ]
        text = "📊 *Data Management*\n\nImport or export your spending data:"

    else:
        # Return to main settings menu
        log_user_action(user_id, "returned to main settings menu")
        # Create the main settings menu with grouped options
        keyboard = [
            # Currency Settings Group
            [InlineKeyboardButton("💱 Currency Settings", callback_data="settings_section:currency")],
            # Category Settings Group
            [InlineKeyboardButton("📋 Category Settings", callback_data="settings_section:category")],
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

    if action == "add_currency":
        # Show common currencies to add
        await show_add_currency_options(update, user_id)

    elif action == "remove_currency":
        # Show user currencies to remove
        await show_remove_currency_options(update, user_id)

    elif action == "main_currency":
        # Show currency selection for setting main currency
        await show_main_currency_options(update, user_id)

    elif action == "add_category":
        # Show common categories to add
        await show_add_category_options(update, user_id)

    elif action == "remove_category":
        # Show user categories to remove
        await show_remove_category_options(update, user_id)

    elif action == "export":
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

    elif action == "import":
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


async def show_add_currency_options(update: Update, user_id: int) -> None:
    """Show common currencies that can be added."""
    query = update.callback_query
    log_user_action(user_id, "viewing add currency options")

    try:
        # Get user's existing currencies
        user_currencies = await db.get_user_currencies(user_id)

        # Filter out currencies the user already has
        available_currencies = [curr for curr in COMMON_CURRENCIES if curr not in user_currencies]

        if not available_currencies:
            # If all common currencies are added, show custom input option
            keyboard = [
                [InlineKeyboardButton("➕ Add Custom Currency", callback_data="settings_custom:add_currency")],
                [InlineKeyboardButton("« Back to Currency Settings", callback_data="settings_section:currency")],
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
                    row.append(InlineKeyboardButton(currency, callback_data=f"settings_add_currency:{currency}"))
            keyboard.append(row)

        # Add custom input and back buttons
        keyboard.append([InlineKeyboardButton("➕ Add Custom Currency", callback_data="settings_custom:add_currency")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="settings_section:currency")])

        await query.edit_message_text(
            "Select a currency to add, or choose 'Add Custom Currency' to enter a custom code:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await handle_db_error(query, "fetching currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching currencies: {str(e)}\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_section:currency")]]
            ),
        )


async def show_remove_currency_options(update: Update, user_id: int) -> None:
    """Show user's currencies that can be removed."""
    query = update.callback_query
    log_user_action(user_id, "viewing remove currency options")

    try:
        # Get user's existing currencies
        currencies = await db.get_user_currencies(user_id)
        if not currencies:
            await query.edit_message_text(
                "You don't have any currencies to remove.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_section:currency")]]
                ),
            )
            return

        # Get current main currency to show with indicator
        current_main = await db.get_user_main_currency(user_id)

        # Create keyboard with all user currencies
        keyboard = []
        for currency in currencies:
            label = f"{currency} {'✓' if currency == current_main else ''}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"settings_remove_currency:{currency}")])

        # Add back button
        keyboard.append([InlineKeyboardButton("« Back", callback_data="settings_section:currency")])

        await query.edit_message_text(
            "Select a currency to remove:"
            + ("\n\n*Note: The currency marked with ✓ is your main currency*" if current_main else ""),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    except Exception as e:
        await handle_db_error(query, "fetching currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching currencies: {str(e)}\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_section:currency")]]
            ),
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
                            InlineKeyboardButton("Add Currency", callback_data="settings_action:add_currency"),
                            InlineKeyboardButton("« Back", callback_data="settings_section:currency"),
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
            keyboard.append([InlineKeyboardButton(label, callback_data=f"settings_set_main_currency:{currency}")])

        # Add back button
        keyboard.append([InlineKeyboardButton("« Back", callback_data="settings_section:currency")])

        await query.edit_message_text(
            "Select your main currency:" + ("\n\n*Current main currency is marked with ✓*" if current_main else ""),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    except Exception as e:
        await handle_db_error(query, "fetching currencies", e)
        await query.edit_message_text(
            f"❌ Error fetching currencies: {str(e)}\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_section:currency")]]
            ),
        )


async def show_add_category_options(update: Update, user_id: int) -> None:
    """Show common categories that can be added."""
    query = update.callback_query
    log_user_action(user_id, "viewing add category options")

    try:
        # Get user's existing categories
        user_categories = await db.get_user_categories(user_id)

        # Filter out categories the user already has
        available_categories = [cat for cat in COMMON_CATEGORIES if cat not in user_categories]

        if not available_categories:
            # If all common categories are added, show custom input option
            keyboard = [
                [InlineKeyboardButton("➕ Add Custom Category", callback_data="settings_custom:add_category")],
                [InlineKeyboardButton("« Back to Category Settings", callback_data="settings_section:category")],
            ]
            await query.edit_message_text(
                "You've already added all common categories.\nYou can still add a custom category:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Show available common categories as buttons (2 per row)
        keyboard = []
        for i in range(0, len(available_categories), 2):  # 2 buttons per row
            row = []
            for j in range(2):
                if i + j < len(available_categories):
                    category = available_categories[i + j]
                    row.append(InlineKeyboardButton(category, callback_data=f"settings_add_category:{category}"))
            keyboard.append(row)

        # Add custom input and back buttons
        keyboard.append([InlineKeyboardButton("➕ Add Custom Category", callback_data="settings_custom:add_category")])
        keyboard.append([InlineKeyboardButton("« Back", callback_data="settings_section:category")])

        await query.edit_message_text(
            "Select a category to add, or choose 'Add Custom Category' for a custom one:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await handle_db_error(query, "fetching categories", e)
        await query.edit_message_text(
            f"❌ Error fetching categories: {str(e)}\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_section:category")]]
            ),
        )


async def show_remove_category_options(update: Update, user_id: int) -> None:
    """Show user's categories that can be removed."""
    query = update.callback_query
    log_user_action(user_id, "viewing remove category options")

    try:
        # Get user's existing categories
        categories = await db.get_user_categories(user_id)
        if not categories:
            await query.edit_message_text(
                "You don't have any categories to remove.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_section:category")]]
                ),
            )
            return

        # Create keyboard with all user categories (2 per row for better display)
        keyboard = []
        row = []
        for i, category in enumerate(categories):
            row.append(InlineKeyboardButton(category, callback_data=f"settings_remove_category:{category}"))

            # Add row after every 2 categories or at the end
            if (i + 1) % 2 == 0 or i == len(categories) - 1:
                keyboard.append(row)
                row = []

        # Add back button
        keyboard.append([InlineKeyboardButton("« Back", callback_data="settings_section:category")])

        await query.edit_message_text("Select a category to remove:", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await handle_db_error(query, "fetching categories", e)
        await query.edit_message_text(
            f"❌ Error fetching categories: {str(e)}\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_section:category")]]
            ),
        )


async def handle_custom_input_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle requests for custom input (currency or category)."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    action_type = query.data.split(":")[1]  # add_currency or add_category

    if action_type == "add_currency":
        # Store request in context and ask for input
        context.user_data["settings_custom_input"] = "currency"
        await query.edit_message_text(
            "Please provide a valid 3-letter currency code (e.g., USD, EUR).\n\n"
            "Reply directly to this message with the currency code.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Cancel", callback_data="settings_section:currency")]]
            ),
        )

    elif action_type == "add_category":
        # Store request in context and ask for input
        context.user_data["settings_custom_input"] = "category"
        await query.edit_message_text(
            "Please provide a category name to add.\n\nReply directly to this message with the category name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Cancel", callback_data="settings_section:category")]]
            ),
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
                [InlineKeyboardButton("➕ Add Another Currency", callback_data="settings_action:add_currency")],
                [InlineKeyboardButton("« Back to Currency Settings", callback_data="settings_section:currency")],
            ]
            await query.edit_message_text(f"✅ {message}", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(
                "Failed to add currency. It might already exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:add_currency")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"adding currency {currency}", e)
        await query.edit_message_text(
            f"❌ Error adding currency: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:add_currency")]]
            ),
        )


async def handle_remove_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle removing a currency from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"removing currency {currency} from settings")

    try:
        # Check if currency is set as main currency
        current_main = await db.get_user_main_currency(user_id)
        if current_main == currency:
            # Confirm removal of main currency
            keyboard = [
                [InlineKeyboardButton("Yes, Remove", callback_data=f"settings_confirm_remove_currency:{currency}")],
                [InlineKeyboardButton("No, Cancel", callback_data="settings_action:remove_currency")],
            ]
            await query.edit_message_text(
                f"⚠️ {currency} is your main currency. Are you sure you want to remove it?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Otherwise proceed with removal
        await process_currency_removal(update, user_id, currency)

    except Exception as e:
        await handle_db_error(query, f"removing currency {currency}", e)
        await query.edit_message_text(
            f"❌ Error removing currency: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:remove_currency")]]
            ),
        )


async def handle_confirm_remove_currency(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle confirmation for removing a main currency."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    currency = query.data.split(":")[1]
    log_user_action(user_id, f"confirmed removal of main currency {currency}")

    await process_currency_removal(update, user_id, currency)


async def process_currency_removal(update: Update, user_id: int, currency: str) -> None:
    """Process the actual removal of a currency."""
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

        # Remove the currency
        success = await db.remove_currency_from_user(user_id, currency)
        if success:
            keyboard = [
                [InlineKeyboardButton("Remove Another Currency", callback_data="settings_action:remove_currency")],
                [InlineKeyboardButton("« Back to Currency Settings", callback_data="settings_section:currency")],
            ]

            # Customize message based on whether it was a main currency
            if current_main == currency:
                message = f"✅ Currency {currency} has been removed from your currencies."
                if await db.get_user_main_currency(user_id):
                    new_main = await db.get_user_main_currency(user_id)
                    message += f"\n\n{new_main} has been set as your new main currency."
            else:
                message = f"✅ Currency {currency} has been successfully removed!"

            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(
                "Failed to remove currency. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:remove_currency")]]
                ),
            )
    except Exception as e:
        logger.error(f"Error processing currency removal: {e}")
        await query.edit_message_text(
            f"❌ Error removing currency: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:remove_currency")]]
            ),
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

        keyboard = [[InlineKeyboardButton("« Back to Currency Settings", callback_data="settings_section:currency")]]
        await query.edit_message_text(
            f"✅ Main currency set to {currency}", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await handle_db_error(query, f"setting main currency to {currency}", e)
        await query.edit_message_text(
            f"❌ Error setting main currency: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:main_currency")]]
            ),
        )


async def handle_add_category(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle adding a category from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"adding category '{category}' from settings")

    try:
        success = await db.add_category_to_user(user_id, category)
        if success:
            keyboard = [
                [InlineKeyboardButton("➕ Add Another Category", callback_data="settings_action:add_category")],
                [InlineKeyboardButton("« Back to Category Settings", callback_data="settings_section:category")],
            ]
            await query.edit_message_text(
                f"✅ Category '{category}' has been successfully added!", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                "Failed to add category. It might already exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:add_category")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"adding category {category}", e)
        await query.edit_message_text(
            f"❌ Error adding category: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:add_category")]]
            ),
        )


async def handle_remove_category(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle removing a category from the settings menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    category = query.data.split(":")[1]
    log_user_action(user_id, f"removing category '{category}' from settings")

    try:
        success = await db.remove_category_from_user(user_id, category)
        if success:
            keyboard = [
                [InlineKeyboardButton("Remove Another Category", callback_data="settings_action:remove_category")],
                [InlineKeyboardButton("« Back to Category Settings", callback_data="settings_section:category")],
            ]
            await query.edit_message_text(
                f"✅ Category '{category}' has been successfully removed!", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                "Failed to remove category. It might not exist or there was an error.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("« Back", callback_data="settings_action:remove_category")]]
                ),
            )
    except Exception as e:
        await handle_db_error(query, f"removing category {category}", e)
        await query.edit_message_text(
            f"❌ Error removing category: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="settings_action:remove_category")]]
            ),
        )


# This function will handle custom text inputs for adding currencies and categories
async def handle_settings_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input for custom currency or category names."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check what type of input we're expecting
    input_type = context.user_data.get("settings_custom_input")
    if not input_type:
        return  # Not in custom input mode

    # Clear the input mode
    del context.user_data["settings_custom_input"]

    if input_type == "currency":
        # Handle currency input
        currency = text.upper()
        if len(currency) != 3 or not currency.isalpha():
            await update.message.reply_text(
                "❌ Invalid input. A currency code must be 3 letters (e.g., USD, EUR).\n\n"
                "Please use /settings to try again."
            )
            return

        try:
            success = await db.add_currency_to_user(user_id, currency)
            if success:
                log_user_action(user_id, f"added custom currency {currency}")

                # Check if this is the first currency and set as main if so
                currencies = await db.get_user_currencies(user_id)
                if len(currencies) == 1:
                    await db.set_user_main_currency(user_id, currency)
                    await update.message.reply_text(
                        f"✅ Currency {currency} has been added and set as your main currency!"
                    )
                else:
                    await update.message.reply_text(f"✅ Currency {currency} has been successfully added!")
            else:
                await update.message.reply_text(
                    "❌ Failed to add currency. It might already exist or there was an error."
                )
        except Exception as e:
            log_user_action(user_id, f"error adding custom currency: {e}")
            await update.message.reply_text(f"❌ Error adding currency: {e}")

    elif input_type == "category":
        # Handle category input
        category = text.strip().capitalize()
        if not category:
            await update.message.reply_text(
                "❌ Invalid input. Category name cannot be empty.\n\nPlease use /settings to try again."
            )
            return

        try:
            success = await db.add_category_to_user(user_id, category)
            if success:
                log_user_action(user_id, f"added custom category '{category}'")
                await update.message.reply_text(f"✅ Category '{category}' has been successfully added!")
            else:
                await update.message.reply_text(
                    "❌ Failed to add category. It might already exist or there was an error."
                )
        except Exception as e:
            log_user_action(user_id, f"error adding custom category: {e}")
            await update.message.reply_text(f"❌ Error adding category: {e}")
