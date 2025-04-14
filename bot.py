from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN
from db import init_db
from handlers.start import start
from handlers.add import add_conversation_handler
from handlers.list import list_spendings
from handlers.remove import remove
from handlers.total import total
from handlers.month import month
from handlers.export import export_spendings
from handlers.non_command import handle_non_command


init_db()

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(add_conversation_handler)
app.add_handler(CommandHandler("remove", remove))
app.add_handler(CommandHandler("list", list_spendings))
app.add_handler(CommandHandler("month", month))
app.add_handler(CommandHandler("total", total))
app.add_handler(CommandHandler("export", export_spendings))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_command))

app.run_polling()
