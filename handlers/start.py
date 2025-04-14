from telegram import Update
from telegram.ext import ContextTypes

from db import populate_default_values


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # Check if the user is new and populate default values
    user_id = update.effective_user.id
    populate_default_values(user_id)

    await update.message.reply_text(
        "👋 Welcome to the Spending Tracker Bot!\n"
        "Use /add to record a new expense.\n"
        "Use /list to view your last 10 expenses.\n"
        "Use /month <month> <year> to view spendings for a specific month.\n"
        "Use /remove <id> to delete spending entry.\n"
        "Use /export to download your spendings as a CSV file.\n"
        "Use /total <category> to view total spendings."
    )
