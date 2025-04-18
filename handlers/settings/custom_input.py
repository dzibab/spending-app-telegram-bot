"""Custom input handlers for settings."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import db
from handlers.common import log_user_action
from utils.validation import validate_category, validate_currency_code


async def handle_custom_input_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle requests for custom input (currency or category)."""
    query = update.callback_query
    await query.answer()

    action_type = query.data.split(":")[1]  # add_currency or add_category

    if action_type == "add_currency":
        # Store request in context and ask for input
        context.user_data["settings_custom_input"] = "currency"
        await query.edit_message_text(
            "Please provide a valid 3-letter currency code (e.g., USD, EUR).\n\n"
            "The code must be exactly 3 letters, representing an ISO 4217 currency code.\n\n"
            "Reply directly to this message with the currency code.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Cancel", callback_data="settings_section:currency")]]
            ),
        )

    elif action_type == "add_category":
        # Store request in context and ask for input
        context.user_data["settings_custom_input"] = "category"
        await query.edit_message_text(
            "Please provide a category name to add.\n\n"
            "The name should be concise and descriptive (maximum 50 characters).\n\n"
            "Reply directly to this message with the category name.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Cancel", callback_data="settings_section:category")]]
            ),
        )


async def handle_settings_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input for custom currency or category names."""
    user_id = update.effective_user.id
    text = update.message.text

    # Check what type of input we're expecting
    input_type = context.user_data.get("settings_custom_input")
    if not input_type:
        return  # Not in custom input mode

    # Clear the input mode
    del context.user_data["settings_custom_input"]

    if input_type == "currency":
        # Handle currency input using validation utility
        is_valid, error_message = validate_currency_code(text)

        if not is_valid:
            await update.message.reply_text(
                f"❌ {error_message}\n\nPlease use /settings and try again with a valid currency code."
            )
            return

        # Get uppercase validated currency
        currency = text.strip().upper()

        try:
            # Check if the currency already exists for this user
            existing_currencies = await db.get_user_currencies(user_id)
            if currency in existing_currencies:
                await update.message.reply_text(
                    f"❌ You already have {currency} in your currencies."
                )
                return

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
                    await update.message.reply_text(
                        f"✅ Currency {currency} has been successfully added!"
                    )
            else:
                await update.message.reply_text(
                    "❌ Failed to add currency. It might already exist or there was an error."
                )
        except Exception as e:
            log_user_action(user_id, f"error adding custom currency: {e}")
            await update.message.reply_text(f"❌ Error adding currency: {e}")

    elif input_type == "category":
        # Handle category input using validation utility
        is_valid, error_message = validate_category(text)

        if not is_valid:
            await update.message.reply_text(
                f"❌ {error_message}\n\nPlease use /settings and try again with a valid category name."
            )
            return

        # Format category name (capitalize first letter)
        category = text.strip().capitalize()

        try:
            # Check if category already exists
            existing_categories = await db.get_user_categories(user_id)
            if category in existing_categories:
                await update.message.reply_text(
                    f"❌ You already have '{category}' in your categories."
                )
                return

            success = await db.add_category_to_user(user_id, category)
            if success:
                log_user_action(user_id, f"added custom category '{category}'")
                await update.message.reply_text(
                    f"✅ Category '{category}' has been successfully added!"
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to add category. It might already exist or there was an error."
                )
        except Exception as e:
            log_user_action(user_id, f"error adding custom category: {e}")
            await update.message.reply_text(f"❌ Error adding category: {e}")
