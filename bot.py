from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import BOT_TOKEN
from constants import BOT_COMMANDS
from db import db
from handlers.category import (
    add_category_conversation_handler,
    handle_remove_category_callback,
    remove_category_handler,
)
from handlers.currency import (
    add_currency_conversation_handler,
    handle_remove_currency_callback,
    remove_currency_handler,
)
from handlers.export import export_spendings_handler
from handlers.list import handle_list_callback, list_spendings_handler
from handlers.main_currency import choose_main_currency_handler, handle_main_currency_callback
from handlers.report import handle_chart_callback, handle_report_callback, report_handler
from handlers.search import handle_search_callback, search_conversation_handler
from handlers.spending import (
    add_spending_conversation_handler,
)
from handlers.start import start_handler
from utils.logging import logger


async def post_init(application: Application) -> None:
    """Initialize bot commands and database."""
    logger.info("Setting up bot commands")
    commands = [
        BotCommand(cmd_info["command"], cmd_info["description"])
        for cmd_info in BOT_COMMANDS.values()
        if cmd_info["command"] != "start"  # Excluding /start
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands configured successfully")

    # Initialize database tables
    logger.info("Initializing database")
    await db.create_tables()


async def shutdown(_: Application) -> None:
    """Close database connection when shutting down."""
    logger.info("Closing database connection")
    await db.close()


if __name__ == "__main__":
    logger.info("Starting Spending Tracker Bot")

    logger.info("Building application")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(shutdown).build()

    # Define handlers in a compact way
    handlers = [
        CommandHandler(BOT_COMMANDS["start"]["command"], start_handler),
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
        CallbackQueryHandler(handle_list_callback, pattern=r"^list_(page|detail|delete):\d+"),
        CallbackQueryHandler(handle_search_callback, pattern=r"^search_(page|detail|back)"),
        add_spending_conversation_handler,
        add_currency_conversation_handler,
        add_category_conversation_handler,
        search_conversation_handler,
    ]

    # Add all handlers to the application
    logger.info("Registering command handlers")
    for handler in handlers:
        app.add_handler(handler)
    logger.info("All handlers registered successfully")

    logger.info("Starting bot polling")
    app.run_polling()
