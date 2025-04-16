from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN
from constants import BOT_COMMANDS
from db import db
from handlers.start import start_handler
from handlers.spending import add_spending_conversation_handler, remove_spending_handler
from handlers.list import list_spendings_handler, handle_list_callback
from handlers.report import report_handler, handle_report_callback, handle_chart_callback
from handlers.export import export_spendings_handler
from handlers.currency import (
    add_currency_conversation_handler,
    remove_currency_handler,
    handle_remove_currency_callback,
    )
from handlers.category import (
    add_category_conversation_handler,
    remove_category_handler,
    handle_remove_category_callback,
    )
from handlers.main_currency import choose_main_currency_handler, handle_main_currency_callback
from utils.logging import logger


async def post_init(application: Application) -> None:
    """Initialize bot commands and database."""
    logger.info("Setting up bot commands")
    commands = [
        BotCommand(cmd_info["command"], cmd_info["description"])
        for cmd_info in BOT_COMMANDS.values() if cmd_info["command"] != "start"  # Excluding /start
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands configured successfully")


if __name__ == "__main__":
    logger.info("Starting Spending Tracker Bot")

    logger.info("Initializing database")
    db.create_tables()

    logger.info("Building application")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Define handlers in a compact way
    handlers = [
        CommandHandler(BOT_COMMANDS["start"]["command"], start_handler),
        CommandHandler(BOT_COMMANDS["remove_spending"]["command"], remove_spending_handler),
        CommandHandler(BOT_COMMANDS["list"]["command"], list_spendings_handler),
        CommandHandler(BOT_COMMANDS["report"]["command"], report_handler),
        CommandHandler(BOT_COMMANDS["remove_currency"]["command"], remove_currency_handler),
        CommandHandler(BOT_COMMANDS["remove_category"]["command"], remove_category_handler),
        CommandHandler(BOT_COMMANDS["export"]["command"], export_spendings_handler),
        CommandHandler(BOT_COMMANDS["main_currency"]["command"], choose_main_currency_handler),
        CallbackQueryHandler(handle_report_callback, pattern=r"^month:\d{2}:\d{4}$"),
        CallbackQueryHandler(handle_chart_callback, pattern=r"^chart:(bar|pie):\d{1,2}:\d{4}$"),
        CallbackQueryHandler(handle_remove_currency_callback, pattern=r"^remove_currency:"),
        CallbackQueryHandler(handle_remove_category_callback, pattern=r"^remove_category:"),
        CallbackQueryHandler(handle_main_currency_callback, pattern=r"^main_currency:"),
        CallbackQueryHandler(handle_list_callback, pattern=r"^list:\d+$"),
        add_spending_conversation_handler,
        add_currency_conversation_handler,
        add_category_conversation_handler,
    ]

    # Add all handlers to the application
    logger.info("Registering command handlers")
    for handler in handlers:
        app.add_handler(handler)
    logger.info("All handlers registered successfully")

    logger.info("Starting bot polling")
    app.run_polling()
