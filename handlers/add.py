from datetime import datetime, date

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db import get_connection
from utils.validation import is_valid_currency

# Define states for the conversation
DESCRIPTION, AMOUNT, CURRENCY, CATEGORY, DATE = range(5)


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("Invalid date format. Use YYYY-MM-DD or DD-MM-YYYY.")


async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please provide a description (or type 'skip' to leave it empty):")
    return DESCRIPTION


async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    if description.lower() != "skip":
        context.user_data["description"] = description
    else:
        context.user_data["description"] = ""
    await update.message.reply_text("Enter the amount:")
    return AMOUNT


async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["amount"] = amount
        await update.message.reply_text("Enter the currency (3-letter ISO code):")
        return CURRENCY
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number:")
        return AMOUNT


async def handle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency = update.message.text.upper()
    if not is_valid_currency(currency):
        await update.message.reply_text("❌ Invalid currency code. Use a valid 3-letter ISO currency:")
        return CURRENCY
    context.user_data["currency"] = currency
    await update.message.reply_text("Enter the category:")
    return CATEGORY


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    context.user_data["category"] = category
    await update.message.reply_text("Enter the date (YYYY-MM-DD or DD-MM-YYYY) or type 'today' for today's date:")
    return DATE


async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_input = update.message.text
    try:
        if date_input.lower() == "today":
            spend_date = date.today()
        else:
            spend_date = parse_date(date_input)
        context.user_data["date"] = spend_date

        # Proceed to save the spending to the database
        await write_spending_to_db(update, context)
        return ConversationHandler.END
    except ValueError as ve:
        await update.message.reply_text(f"❌ {ve}\nPlease enter the date again:")
        return DATE
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return ConversationHandler.END


async def write_spending_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        description = context.user_data["description"]
        amount = context.user_data["amount"]
        currency = context.user_data["currency"]
        category = context.user_data["category"]
        spend_date = context.user_data["date"]

        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO spendings (user_id, description, amount, currency, category, date) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, description, amount, currency, category, spend_date.isoformat())
            )
            spending_id = cursor.lastrowid  # Get the ID of the last inserted record

        await update.message.reply_text(
            f"✅ Spending added successfully!\n"
            f"ID: {spending_id}\n"
            f"Description: {description or 'None'}\n"
            f"Amount: {amount} {currency}\n"
            f"Category: {category}\n"
            f"Date: {spend_date}",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error while saving to the database: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Define the ConversationHandler
add_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add", start_add)],
    states={
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency)],
        CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
