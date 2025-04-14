from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from config import BOT_TOKEN
from db import create_tables
from handlers.start import start
from handlers.add import add_conversation_handler
from handlers.list import list_spendings
from handlers.remove import remove
from handlers.total import total
from handlers.month import month, handle_month_selection
from handlers.export import export_spendings
from handlers.non_command import handle_non_command


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("add", "Add a spending"),
        BotCommand("remove", "Remove a spending"),
        BotCommand("list", "List spendings"),
        BotCommand("month", "Select month"),
        BotCommand("total", "Get total spendings"),
        BotCommand("export", "Export spendings"),
    ]
    await application.bot.set_my_commands(commands)


if __name__ == "__main__":
    create_tables()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conversation_handler)
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("list", list_spendings))
    app.add_handler(CommandHandler("month", month))
    app.add_handler(CallbackQueryHandler(handle_month_selection, pattern=r"^month:\d{2}:\d{4}$"))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("export", export_spendings))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_command))

    app.run_polling()
