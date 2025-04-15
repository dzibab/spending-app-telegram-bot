import os

from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
