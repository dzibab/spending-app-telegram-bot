from datetime import datetime, date

from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection
from utils.validation import is_valid_currency


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("Invalid date format. Use YYYY-MM-DD or DD-MM-YYYY.")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /add <description?> <amount> <currency> <category> <date?>"
            )
            return

        user_id = update.effective_user.id

        # Handle optional description and date
        if len(args) == 3:
            # Only amount, currency, category
            description = ""
            amount, currency, category = args
            spend_date = date.today()
        elif len(args) == 4:
            # Either [desc, amount, currency, category] or [amount, currency, category, date]
            try:
                spend_date = parse_date(args[3])
                description = ""
                amount, currency, category = args[:3]
            except ValueError:
                description, amount, currency, category = args
                spend_date = date.today()
        elif len(args) == 5:
            description, amount, currency, category = args[:4]
            spend_date = parse_date(args[4])
        else:
            await update.message.reply_text("Too many arguments.")
            return

        if not is_valid_currency(currency):
            await update.message.reply_text("❌ Invalid currency code. Use a valid 3-letter ISO currency.")
            return
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO spendings (user_id, description, amount, currency, category, date) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, description, float(amount), currency, category, spend_date.isoformat())
            )
            spending_id = cursor.lastrowid  # Get the ID of the last inserted record

        await update.message.reply_text(
            f"✅ Spending added successfully!\n"
            f"ID: {spending_id}\n"
            f"Description: {description or 'None'}\n"
            f"Amount: {amount} {currency}\n"
            f"Category: {category}\n"
            f"Date: {spend_date}"
        )
    except ValueError as ve:
        await update.message.reply_text(f"❌ {ve}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
