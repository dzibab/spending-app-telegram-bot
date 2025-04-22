import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure the logger
logger = logging.getLogger("spending_bot")
logger.setLevel(logging.DEBUG)

# Create formatters
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)

# Create console handler with INFO level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(console_formatter)

# Create file handler with DEBUG level and rotation
log_file = f"logs/spending_bot_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=5,
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Log startup message
logger.info("Logger initialized")
