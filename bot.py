from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN
from db import create_tables
from handlers.start import start
from handlers.spending import add_spending_conversation_handler, remove_spending
from handlers.list import list_spendings
from handlers.total import total
from handlers.month import month, handle_month_selection
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


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("add_spending", "Add a spending"),
        BotCommand("remove_spending", "Remove a spending"),
        BotCommand("add_category", "Add a category"),
        BotCommand("remove_category", "Remove a category"),
        BotCommand("list", "List spendings"),
        BotCommand("month", "Select month"),
        BotCommand("total", "Get total spendings"),
        BotCommand("add_currency", "Add a currency"),
        BotCommand("remove_currency", "Remove a currency"),
        BotCommand("export", "Export spendings"),
    ]
    await application.bot.set_my_commands(commands)


if __name__ == "__main__":
    create_tables()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_spending_conversation_handler)
    app.add_handler(CommandHandler("remove_spending", remove_spending))
    app.add_handler(CommandHandler("list", list_spendings))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CallbackQueryHandler(handle_month_selection, pattern=r"^month:\d{2}:\d{4}$"))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(add_currency_conversation_handler)
    app.add_handler(CommandHandler("remove_currency", remove_currency_handler))
    app.add_handler(CallbackQueryHandler(handle_remove_currency_callback, pattern=r"^remove_currency:"))
    app.add_handler(add_category_conversation_handler)
    app.add_handler(CommandHandler("remove_category", remove_category_handler))
    app.add_handler(CallbackQueryHandler(handle_remove_category_callback, pattern=r"^remove_category:"))
    app.add_handler(CommandHandler("export", export_spendings))

    app.run_polling()
