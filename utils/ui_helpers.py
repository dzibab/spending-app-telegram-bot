"""UI/message formatting helpers for spendings bot."""

from telegram import Update


def format_spending_button_text(spending) -> str:
    """Format the button text for a spending entry."""
    if hasattr(spending, "id"):
        desc = spending.description
        amount = spending.amount
        currency = spending.currency
        cat = spending.category
        dt = spending.date
    else:
        _, desc, amount, currency, cat, dt = spending
    button_text = f"{dt} | {amount} {currency} | {cat}"
    if desc:
        button_text += f" | {desc[:20]}"
    return button_text


async def handle_no_results(update: Update, message: str) -> None:
    """Handle case when no results are available."""
    if update.callback_query:
        await update.callback_query.edit_message_text(f"📭 {message}.")
    else:
        await update.message.reply_text(f"📭 {message}.")


async def format_spending_details(spending) -> str:
    """Format spending details for display."""
    return (
        f"📝 Spending Details:\n\n"
        f"Date: {spending.date}\n"
        f"Amount: {spending.amount} {spending.currency}\n"
        f"Category: {spending.category}\n"
        f"Description: {spending.description or 'No description'}"
    )
