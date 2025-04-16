from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN
from db import create_tables
from handlers.start import start_handler
from handlers.spending import add_spending_conversation_handler, remove_spending_handler
from handlers.list import list_spendings_handler
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
    logger.info("Setting up bot commands")
    commands = [
        BotCommand("add_spending", "Add a spending"),
        BotCommand("remove_spending", "Remove a spending"),
        BotCommand("add_category", "Add a category"),
        BotCommand("remove_category", "Remove a category"),
        BotCommand("add_currency", "Add a currency"),
        BotCommand("remove_currency", "Remove a currency"),
        BotCommand("list", "List spendings"),
        BotCommand("report", "View spending reports"),
        BotCommand("export", "Export spendings"),
        BotCommand("main_currency", "Choose main currency"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands configured successfully")


if __name__ == "__main__":
    logger.info("Starting Spending Tracker Bot")

    logger.info("Initializing database")
    create_tables()

    logger.info("Building application")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Define handlers in a compact way
    handlers = [
        CommandHandler("start", start_handler),
        CommandHandler("remove_spending", remove_spending_handler),
        CommandHandler("list", list_spendings_handler),
        CommandHandler("report", report_handler),
        CommandHandler("remove_currency", remove_currency_handler),
        CommandHandler("remove_category", remove_category_handler),
        CommandHandler("export", export_spendings_handler),
        CommandHandler("main_currency", choose_main_currency_handler),
        CallbackQueryHandler(handle_report_callback, pattern=r"^month:\d{2}:\d{4}$"),
        CallbackQueryHandler(handle_chart_callback, pattern=r"^chart:(bar|pie):\d{1,2}:\d{4}$"),
        CallbackQueryHandler(handle_remove_currency_callback, pattern=r"^remove_currency:"),
        CallbackQueryHandler(handle_remove_category_callback, pattern=r"^remove_category:"),
        CallbackQueryHandler(handle_main_currency_callback, pattern=r"^main_currency:"),
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
