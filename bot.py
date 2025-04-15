from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN
from db import create_tables
from handlers.start import start
from handlers.spending import add_spending_conversation_handler, remove_spending
from handlers.list import list_spendings
from handlers.total import total
from handlers.month import month, handle_month_selection, handle_chart_selection
from handlers.export import export_spendings
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
from handlers.main_currency import choose_main_currency, handle_main_currency_selection


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("add_spending", "Add a spending"),
        BotCommand("remove_spending", "Remove a spending"),
        BotCommand("add_category", "Add a category"),
        BotCommand("remove_category", "Remove a category"),
        BotCommand("add_currency", "Add a currency"),
        BotCommand("remove_currency", "Remove a currency"),
        BotCommand("list", "List spendings"),
        BotCommand("month", "Select month"),
        BotCommand("total", "Get total spendings"),
        BotCommand("export", "Export spendings"),
        BotCommand("main_currency", "Choose main currency"),
    ]
    await application.bot.set_my_commands(commands)


if __name__ == "__main__":
    create_tables()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Define handlers in a compact way
    handlers = [
        CommandHandler("start", start),
        CommandHandler("remove_spending", remove_spending),
        CommandHandler("list", list_spendings),
        CommandHandler("month", month),
        CommandHandler("total", total),
        CommandHandler("remove_currency", remove_currency_handler),
        CommandHandler("remove_category", remove_category_handler),
        CommandHandler("export", export_spendings),
        CommandHandler("main_currency", choose_main_currency),
        CallbackQueryHandler(handle_month_selection, pattern=r"^month:\d{2}:\d{4}$"),
        CallbackQueryHandler(handle_chart_selection, pattern=r"^chart:(bar|pie):\d{1,2}:\d{4}$"),
        CallbackQueryHandler(handle_remove_currency_callback, pattern=r"^remove_currency:"),
        CallbackQueryHandler(handle_remove_category_callback, pattern=r"^remove_category:"),
        CallbackQueryHandler(handle_main_currency_selection, pattern=r"^main_currency:"),
        add_spending_conversation_handler,
        add_currency_conversation_handler,
        add_category_conversation_handler,
    ]

    # Add all handlers to the application
    for handler in handlers:
        app.add_handler(handler)

    app.run_polling()
