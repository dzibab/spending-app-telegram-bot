import os

from dotenv import load_dotenv

from utils.logging import logger


logger.info("Loading environment variables")
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    raise ValueError("BOT_TOKEN environment variable is required")

EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
if not EXCHANGE_API_KEY:
    logger.error("EXCHANGE_API_KEY not found in environment variables")
    raise ValueError("EXCHANGE_API_KEY environment variable is required")

logger.info("Configuration loaded successfully")
