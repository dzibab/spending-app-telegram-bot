
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from constants import BOT_COMMANDS
from db import db
from handlers.common import cancel, create_keyboard_markup, handle_db_error, log_user_action
from utils.validation import (
    validate_amount,
    validate_category,
    validate_currency_code,
    validate_date,
    validate_description,
)

# Define states for the conversation
DESCRIPTION, AMOUNT, CURRENCY, CATEGORY, DATE = range(5)


async def start_add(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log_user_action(user_id, "initiated adding a spending")

    # Add a 'skip' button for the description state
    keyboard = create_keyboard_markup(["No description"])
    await update.message.reply_text(
        "Please provide a description:",
        reply_markup=keyboard,
    )
    return DESCRIPTION


async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    if description.lower() != "no description":
        # Validate description
        is_valid, error_message = validate_description(description)
        if not is_valid:
            await update.message.reply_text(
                f"❌ {error_message}\nPlease provide a valid description:"
            )
            return DESCRIPTION

        context.user_data["description"] = description
    else:
        context.user_data["description"] = ""
    await update.message.reply_text("Enter the amount:", reply_markup=ReplyKeyboardRemove())
    return AMOUNT


async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_str = update.message.text
    # Use validation utility
    is_valid, result = validate_amount(amount_str)

    if not is_valid:
        await update.message.reply_text(f"❌ {result}\nPlease enter a valid amount:")
        return AMOUNT

    # Store valid amount
    amount = result
    context.user_data["amount"] = amount

    # Fetch user-specific currencies
    user_id = update.effective_user.id
    currencies = await db.get_user_currencies(user_id)

    # Create a keyboard with currency options
    keyboard = create_keyboard_markup(currencies)

    # Get main currency to show it first
    main_currency = await db.get_user_main_currency(user_id)
    hint = f" (your main currency is {main_currency})" if main_currency else ""

    await update.message.reply_text(f"Enter the currency{hint}:", reply_markup=keyboard)
    return CURRENCY


async def handle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    currencies = await db.get_user_currencies(user_id)

    # Validate currency code format first
    currency = update.message.text.upper().strip()
    is_valid, error_message = validate_currency_code(currency)

    if not is_valid:
        keyboard = create_keyboard_markup(currencies)
        await update.message.reply_text(
            f"❌ {error_message}\nPlease select a valid currency from the options below:",
            reply_markup=keyboard,
        )
        return CURRENCY

    # Then validate that the user has this currency
    if currency not in currencies:
        keyboard = create_keyboard_markup(currencies)
        await update.message.reply_text(
            f"❌ Currency '{currency}' is not in your list of currencies.\nPlease select a valid currency from the options below:",
            reply_markup=keyboard,
        )
        return CURRENCY

    context.user_data["currency"] = currency

    # Fetch user-specific categories
    categories = await db.get_user_categories(user_id)

    # Add categories as buttons
    keyboard = create_keyboard_markup(categories)
    await update.message.reply_text("Enter the category:", reply_markup=keyboard)
    return CATEGORY


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    category = update.message.text

    # Validate category name
    is_valid, error_message = validate_category(category)
    if not is_valid:
        categories = await db.get_user_categories(user_id)
        keyboard = create_keyboard_markup(categories)
        await update.message.reply_text(
            f"❌ {error_message}\nPlease enter a valid category:",
            reply_markup=keyboard,
        )
        return CATEGORY

    # Validate that the user has this category
    categories = await db.get_user_categories(user_id)
    if category not in categories:
        keyboard = create_keyboard_markup(categories)
        await update.message.reply_text(
            f"❌ Category '{category}' is not in your list of categories.\nPlease select a valid category from the options below:",
            reply_markup=keyboard,
        )
        return CATEGORY

    context.user_data["category"] = category

    # Add a 'today' button for the date state
    keyboard = create_keyboard_markup(["Today"])
    await update.message.reply_text(
        "Enter the date or press 'Today' for today's date:",
        reply_markup=keyboard,
    )
    return DATE


async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_input = update.message.text

    # Use validation utility
    is_valid, result = validate_date(date_input)

    if not is_valid:
        keyboard = create_keyboard_markup(["Today"])
        await update.message.reply_text(
            f"❌ {result}\nPlease enter the date again or press 'Today' for today's date:",
            reply_markup=keyboard,
        )
        return DATE

    # Store the validated date
    spend_date = result.date()
    context.user_data["date"] = spend_date

    # Proceed to save the spending to the database
    await write_spending_to_db(update, context)
    return ConversationHandler.END


async def write_spending_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        description = context.user_data["description"]
        amount = context.user_data["amount"]
        currency = context.user_data["currency"]
        category = context.user_data["category"]
        spend_date = context.user_data["date"]

        await db.add_spending(
            user_id, description, amount, currency, category, spend_date.isoformat()
        )
        log_user_action(
            user_id, f"added spending: {amount} {currency} for {category} on {spend_date}"
        )

        await update.message.reply_text(
            f"✅ Spending added successfully!\n"
            f"Description: {description or 'None'}\n"
            f"Amount: {amount} {currency}\n"
            f"Category: {category}\n"
            f"Date: {spend_date}",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        await handle_db_error(update, "while saving spending", e)


# Define the ConversationHandler
add_spending_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add_spending", start_add)],
    states={
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_currency)],
        CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
    },
    fallbacks=[CommandHandler(cmd_info["command"], cancel) for cmd_info in BOT_COMMANDS.values()],
)
