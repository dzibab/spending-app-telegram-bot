from telegram import Update
from telegram.ext import ContextTypes

from constants import BOT_USAGE_INSTRUCTIONS
from db import db
from handlers.common import handle_db_error, log_user_action


async def start_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log_user_action(user_id, "started the bot")

    try:
        # Check if the user is new and populate default values
        await db.initialize_user_defaults(user_id)
        log_user_action(user_id, "initialized with default settings")

        await update.message.reply_text(
            f"👋 Welcome to the Spending Tracker Bot!\n{BOT_USAGE_INSTRUCTIONS}"
        )
    except Exception as e:
        await handle_db_error(update, "initializing your account", e)
