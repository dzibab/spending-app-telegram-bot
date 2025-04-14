from telegram import Update
from telegram.ext import ContextTypes


async def handle_non_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Available commands message
    commands_message = (
        "Here are the available commands you can use:\n\n"
        "/start - Start the bot\n"
        "/add <description> <amount> <currency> <category> <date> - Add a spending\n"
        "/list - View all your spendings\n"
        "/remove <spending_id> - Remove a spending\n"
        "/total - View your total spending\n"
        "/month <month> <year> - View spendings for a specific month\n"
        "/export - Export your spendings to a CSV file\n"
    )

    # Reply to the user with the list of commands
    await update.message.reply_text(commands_message)
