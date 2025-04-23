"""UI/message formatting helpers for spendings bot."""

from telegram import Update

from utils.logging import logger


def format_spending_button_text(spending) -> str:
    """Format the button text for a spending entry."""
    try:
        if hasattr(spending, "id"):
            desc = spending.description
            amount = spending.amount
            currency = spending.currency
            cat = spending.category
            dt = spending.date
            spending_id = spending.id
        else:
            spending_id, desc, amount, currency, cat, dt = spending

        logger.debug(f"Formatting spending button text for spending ID {spending_id}")
        button_text = f"{dt} | {amount} {currency} | {cat}"
        if desc:
            # Truncate long descriptions
            truncated = desc[:20] + ("..." if len(desc) > 20 else "")
            button_text += f" | {truncated}"

        logger.debug(f"Generated button text: '{button_text}'")
        return button_text
    except Exception as e:
        logger.error(f"Error formatting spending button text: {e}")
        # Return a safe fallback to avoid UI errors
        return "Error: Could not format spending"


async def handle_no_results(update: Update, message: str) -> None:
    """Handle case when no results are available."""
    user_id = update.effective_user.id
    logger.debug(f"Handling no results for user {user_id}: {message}")

    try:
        if update.callback_query:
            logger.debug("Sending no results message via callback query")
            await update.callback_query.edit_message_text(f"📭 {message}.")
        else:
            logger.debug("Sending no results message via direct reply")
            await update.message.reply_text(f"📭 {message}.")
        logger.debug(f"No results message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error handling no results display for user {user_id}: {e}")


async def format_spending_details(spending) -> str:
    """Format spending details for display."""
    try:
        logger.debug(f"Formatting detailed view for spending ID {spending.id}")
        formatted = (
            f"📝 Spending Details:\n\n"
            f"Date: {spending.date}\n"
            f"Amount: {spending.amount} {spending.currency}\n"
            f"Category: {spending.category}\n"
            f"Description: {spending.description or 'No description'}"
        )
        logger.debug(f"Generated detailed spending view for ID {spending.id}")
        return formatted
    except Exception as e:
        logger.error(f"Error formatting spending details: {e}")
        return "Error: Could not display spending details"
