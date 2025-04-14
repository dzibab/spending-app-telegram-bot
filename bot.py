from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config import BOT_TOKEN
from db import create_tables
from handlers.start import start
from handlers.spending import add_spending_conversation_handler, remove_spending
from handlers.list import list_spendings
from handlers.total import total
from handlers.month import month, handle_month_selection
from handlers.export import export_spendings
from handlers.non_command import handle_non_command
from handlers.currency import add_currency_handler, remove_currency_handler


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("add_spending", "Add a spending"),
        BotCommand("remove_spending", "Remove a spending"),
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
    app.add_handler(CommandHandler("add_currency", add_currency_handler))
    app.add_handler(CommandHandler("remove_currency", remove_currency_handler))
    app.add_handler(CommandHandler("export", export_spendings))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_command))

    app.run_polling()
