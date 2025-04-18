from telegram import Update
from telegram.ext import ContextTypes

from db import db
from constants import BOT_USAGE_INSTRUCTIONS
from utils.logging import logger


async def start_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot.")

    # Check if the user is new and populate default values
    await db.initialize_user_defaults(user_id)

    await update.message.reply_text(
        "👋 Welcome to the Spending Tracker Bot!\n"
        f"{BOT_USAGE_INSTRUCTIONS}"
        )
