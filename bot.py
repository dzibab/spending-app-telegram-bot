from telegram.ext import Application, CommandHandler

from config import BOT_TOKEN
from db import init_db
from handlers.start import start
from handlers.add import add
from handlers.list import list_spendings
from handlers.remove import remove
from handlers.total import total


init_db()

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_spendings))
app.add_handler(CommandHandler("remove", remove))
app.add_handler(CommandHandler("total", total))

app.run_polling()
