from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Spending Tracker Bot!\n"
        "Use /add <description?> <amount> <currency> <category> <date?> to record a new expense.\n"
        "Use /list to view your last 10 expenses.\n"
        "Use /month <month> <year> to view spendings for a specific month.\n"
        "Use /remove <id> to delete spending entry.\n"
        "Use /export to download your spendings as a CSV file.\n"
        "Use /total <category> to view total spendings."
    )
