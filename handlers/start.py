from telegram import Update
from telegram.ext import ContextTypes

from db import populate_default_values
from constants import BOT_USAGE_INSTRUCTIONS


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # Check if the user is new and populate default values
    user_id = update.effective_user.id
    populate_default_values(user_id)

    await update.message.reply_text(
        "👋 Welcome to the Spending Tracker Bot!\n"
        f"{BOT_USAGE_INSTRUCTIONS}"
        )
