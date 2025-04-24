"""Data deletion functionality for settings."""

import uuid
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.common import handle_db_error, log_user_action
from handlers.settings.utils import create_back_button, create_error_keyboard
from utils.logging import logger
from utils.user_utils import delete_all_user_data


async def show_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show initial confirmation screen for data deletion."""
    query = update.callback_query
    user_id = query.from_user.id
    log_user_action(user_id, "requesting data deletion confirmation")

    # Generate a unique confirmation code for this deletion request
    # This adds an additional security layer requiring user to type the code
    confirmation_code = str(uuid.uuid4())[:8].upper()

    # Store the confirmation code with an expiration time (10 minutes)
    expires = datetime.now() + timedelta(minutes=10)
    context.user_data["delete_confirmation"] = {"code": confirmation_code, "expires_at": expires}

    keyboard = [
        [InlineKeyboardButton("❌ No, Keep My Data", callback_data="settings_section:data")],
        [InlineKeyboardButton("✅ Yes, Continue", callback_data="confirm_delete:step1")],
    ]

    await query.edit_message_text(
        "🚫 *Delete All Your Data*\n\n"
        "⚠️ *WARNING: This action cannot be undone!* ⚠️\n\n"
        "This will permanently delete:\n"
        "• All your spending records\n"
        "• All your categories\n"
        "• All your currencies\n"
        "• Your settings\n\n"
        "Are you sure you want to continue?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_final_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the second step confirmation with verification code."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Get the stored confirmation data
    confirmation_data = context.user_data.get("delete_confirmation", {})
    confirmation_code = confirmation_data.get("code")
    expires_at = confirmation_data.get("expires_at")

    # Check if confirmation is still valid
    if not confirmation_code or not expires_at or datetime.now() > expires_at:
        # Expired or missing confirmation data
        await query.edit_message_text(
            "⚠️ Your deletion request has expired for security reasons.\n\n"
            "If you still want to delete your data, please start over.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "« Back to Data Management", callback_data="settings_section:data"
                        )
                    ]
                ]
            ),
        )
        return

    # Display the confirmation code and ask user to confirm
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="settings_section:data")],
        [
            InlineKeyboardButton(
                f"✅ Confirm Code: {confirmation_code}",
                callback_data=f"execute_delete:{confirmation_code}",
            )
        ],
    ]

    await query.edit_message_text(
        "🔒 *Final Verification Required*\n\n"
        "To confirm that you want to permanently delete ALL your data, "
        f"please verify the following code: `{confirmation_code}`\n\n"
        "⚠️ *This action CANNOT be undone and ALL your data will be PERMANENTLY deleted!* ⚠️",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def execute_data_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute the actual data deletion after all confirmations."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Get the stored confirmation data and entered code
    confirmation_data = context.user_data.get("delete_confirmation", {})
    stored_code = confirmation_data.get("code")
    expires_at = confirmation_data.get("expires_at")

    # Extract the code from callback data
    entered_code = query.data.split(":")[1] if ":" in query.data else None

    # Validate that codes match and haven't expired
    if not stored_code or not expires_at or datetime.now() > expires_at:
        # Expired confirmation
        await query.edit_message_text(
            "⚠️ Your deletion request has expired for security reasons.\n\n"
            "If you still want to delete your data, please start over.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "« Back to Data Management", callback_data="settings_section:data"
                        )
                    ]
                ]
            ),
        )
        return

    if not entered_code or entered_code != stored_code:
        # Invalid code
        await query.edit_message_text(
            "❌ *Verification Failed*\n\n"
            "The verification code is incorrect. Your data has NOT been deleted.\n\n"
            "If you still want to delete your data, please start over.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "« Back to Data Management", callback_data="settings_section:data"
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )
        return

    # All checks passed, proceed with deletion
    try:
        log_user_action(user_id, "confirmed data deletion with verification code")

        # Show processing message
        await query.edit_message_text(
            "⏳ Processing your request...\n\nDeleting all your data...",
        )

        # Execute the deletion
        success, message = await delete_all_user_data(user_id)

        # Clear the confirmation data
        context.user_data.pop("delete_confirmation", None)

        if success:
            # Show success message
            await query.edit_message_text(
                "✅ *Data Deleted Successfully*\n\n"
                "All your data has been permanently deleted from our system.\n\n"
                "The next time you use the bot, default settings will be restored.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "« Back to Settings", callback_data="settings_back:main"
                            )
                        ]
                    ]
                ),
                parse_mode="Markdown",
            )
        else:
            # Show error message
            await query.edit_message_text(
                f"❌ *Error Deleting Data*\n\n{message}\n\nPlease try again later.",
                reply_markup=create_error_keyboard("settings_section:data"),
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Error during data deletion for user {user_id}: {e}")
        await handle_db_error(query, "deleting user data", e)
        await query.edit_message_text(
            f"❌ *An Unexpected Error Occurred*\n\nError deleting your data: {e}",
            reply_markup=create_error_keyboard("settings_section:data"),
            parse_mode="Markdown",
        )
