from io import BytesIO
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) != 2:
        await update.message.reply_text("Usage: /month <month> <year>")
        return

    try:
        month = int(args[0])
        year = int(args[1])

        if not (1 <= month <= 12):
            await update.message.reply_text("❌ Please enter a valid month (1-12).")
            return
    except ValueError:
        await update.message.reply_text("❌ Invalid month or year. Please provide numeric values.")
        return

    # Query to fetch spending data for the specified month and year
    query = """
        SELECT category, SUM(amount) as total
        FROM spendings
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category
    """
    with get_connection() as conn:
        cursor = conn.execute(query, (user_id, str(year), f"{month:02d}"))
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 No spendings found for this month.")
        return

    # Prepare data for plotting
    data = pd.DataFrame(rows, columns=["category", "total"])

    # Plot the chart
    plt.figure(figsize=(10, 6))
    plt.bar(data['category'], data['total'], color='skyblue')
    plt.xlabel('Category')
    plt.ylabel('Total Spending')
    plt.title(f"Spending by Category for {datetime(year, month, 1).strftime('%B %Y')}")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Send the chart as a photo
    await update.message.reply_photo(photo=buf)
    buf.close()
