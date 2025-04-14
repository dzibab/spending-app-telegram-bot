from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Spending Tracker Bot!\n"
        "Use /add to record a new expense.\n"
        "Use /list to view your expenses.\n"
        "Use /remove to delete an entry.\n"
        "Use /total to view total spendings."
    )
