import traceback

from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from constants import BOT_COMMANDS
from db import db
from handlers.category import (
    add_category_conversation_handler,
    handle_remove_category_callback,
    remove_category_handler,
)
from handlers.currency import (
    add_currency_conversation_handler,
    handle_remove_currency_callback,
    remove_currency_handler,
)
from handlers.export_csv import export_spendings_handler, handle_export_callback
from handlers.import_csv import (
    handle_csv_file_upload,
    handle_import_cancel,
    import_conversation_handler,
    send_import_template,
)
from handlers.list import handle_list_callback, list_spendings_handler
from handlers.main_currency import choose_main_currency_handler, handle_main_currency_callback
from handlers.report import handle_chart_callback, handle_report_callback, report_handler
from handlers.search import handle_search_callback, search_conversation_handler
from handlers.settings import (
    handle_add_category,
    handle_add_currency,
    handle_confirm_remove_currency,
    handle_custom_input_request,
    handle_remove_category,
    handle_remove_currency,
    handle_set_main_currency,
    handle_settings_action,
    handle_settings_callback,
    handle_settings_text_input,
    settings_handler,
)
from handlers.spending import (
    add_spending_conversation_handler,
)
from handlers.start import start_handler
from utils.logging import logger


async def post_init(application: Application) -> None:
    """Initialize bot commands and database."""
    logger.info("Setting up bot commands")

    # Only register frequently used commands in the main menu
    frequently_used_commands = [
        BotCommand(cmd_info["command"], cmd_info["description"])
        for _, cmd_info in BOT_COMMANDS.items()
        if cmd_info.get("frequency") in ["high", "medium"] and cmd_info.get("command") != "start"
    ]

    await application.bot.set_my_commands(frequently_used_commands)
    logger.info("Bot commands configured successfully")

    # Initialize database tables
    logger.info("Initializing database")
    await db.create_tables()


async def shutdown(_: Application) -> None:
    """Close database connection when shutting down."""
    logger.info("Closing database connection")
    await db.close()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the dispatcher."""
    logger.error(f"Exception while handling an update: {context.error}")

    # Extract the error info
    error_message = str(context.error)
    logger.error(f"Error message: {error_message}")

    # Log more detailed traceback in the logger

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception traceback:\n{tb_string}")

    # Send a message to the user only if we have an update object
    if update and hasattr(update, "effective_message") and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, something went wrong. The error has been logged and will be addressed.\n\n"
            "Please try again or contact support if the issue persists."
        )

    # If it's a callback query, we need to answer it to clear the loading state
    if update and hasattr(update, "callback_query") and update.callback_query:
        try:
            await update.callback_query.answer("An error occurred. Please try again.")
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")


if __name__ == "__main__":
    logger.info("Starting Spending Tracker Bot")

    logger.info("Building application")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(shutdown).build()

    # Define handlers in a compact way
    handlers = [
        # Standard command handlers
        CommandHandler(BOT_COMMANDS["start"]["command"], start_handler),
        CommandHandler(BOT_COMMANDS["list"]["command"], list_spendings_handler),
        CommandHandler(BOT_COMMANDS["report"]["command"], report_handler),
        CommandHandler(BOT_COMMANDS["remove_currency"]["command"], remove_currency_handler),
        CommandHandler(BOT_COMMANDS["remove_category"]["command"], remove_category_handler),
        CommandHandler(BOT_COMMANDS["export"]["command"], export_spendings_handler),
        CommandHandler(BOT_COMMANDS["main_currency"]["command"], choose_main_currency_handler),
        CommandHandler(BOT_COMMANDS["settings"]["command"], settings_handler),
        # Settings menu handlers
        CallbackQueryHandler(handle_settings_action, pattern=r"^settings_action:"),
        CallbackQueryHandler(handle_custom_input_request, pattern=r"^settings_custom:"),
        CallbackQueryHandler(handle_add_currency, pattern=r"^settings_add_currency:"),
        CallbackQueryHandler(handle_remove_currency, pattern=r"^settings_remove_currency:"),
        CallbackQueryHandler(handle_confirm_remove_currency, pattern=r"^settings_confirm_remove_currency:"),
        CallbackQueryHandler(handle_set_main_currency, pattern=r"^settings_set_main_currency:"),
        CallbackQueryHandler(handle_add_category, pattern=r"^settings_add_category:"),
        CallbackQueryHandler(handle_remove_category, pattern=r"^settings_remove_category:"),
        # Original handlers
        CallbackQueryHandler(handle_report_callback, pattern=r"^month:\d{2}:\d{4}$"),
        CallbackQueryHandler(handle_chart_callback, pattern=r"^chart:(bar|pie):\d{1,2}:\d{4}$"),
        CallbackQueryHandler(handle_remove_currency_callback, pattern=r"^remove_currency:"),
        CallbackQueryHandler(handle_remove_category_callback, pattern=r"^remove_category:"),
        CallbackQueryHandler(handle_main_currency_callback, pattern=r"^main_currency:"),
        CallbackQueryHandler(handle_list_callback, pattern=r"^list_(page|detail|delete):\d+"),
        CallbackQueryHandler(handle_search_callback, pattern=r"^search_(page|detail|back|delete)"),
        CallbackQueryHandler(handle_settings_callback, pattern=r"^settings_section:"),
        CallbackQueryHandler(handle_settings_callback, pattern=r"^settings_back:"),
        CallbackQueryHandler(handle_settings_callback, pattern=r"^settings_cmd:"),
        # Export and import handlers
        CallbackQueryHandler(handle_export_callback, pattern=r"^export_range:"),
        CallbackQueryHandler(handle_export_callback, pattern=r"^export_back:"),
        CallbackQueryHandler(handle_import_cancel, pattern=r"^import_cancel"),
        CallbackQueryHandler(send_import_template, pattern=r"^import_template"),
        # Conversation handlers
        add_spending_conversation_handler,
        add_currency_conversation_handler,
        add_category_conversation_handler,
        search_conversation_handler,
        import_conversation_handler,
        # Add a handler for custom input text messages
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_text_input),
        # CSV file upload handler - placed at the top for highest priority
        MessageHandler(filters.Document.FileExtension("csv"), handle_csv_file_upload),
    ]

    # Add all handlers to the application
    logger.info("Registering command handlers")
    for handler in handlers:
        app.add_handler(handler)
    logger.info("All handlers registered successfully")

    # Register the error handler
    app.add_error_handler(error_handler)

    logger.info("Starting bot polling")
    app.run_polling()
