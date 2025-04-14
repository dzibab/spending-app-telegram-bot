from telegram import Update
from telegram.ext import ContextTypes

from constants import BOT_USAGE_INSTRUCTIONS


async def handle_non_command(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # Available commands message
    commands_message = (
        "Here are the available commands you can use:\n"
        f"{BOT_USAGE_INSTRUCTIONS}"
    )

    # Reply to the user with the list of commands
    await update.message.reply_text(commands_message)
