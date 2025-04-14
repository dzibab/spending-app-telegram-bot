import csv
import io

from telegram import Update
from telegram.ext import ContextTypes

from db import get_connection


async def export_spendings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the user ID
    user_id = update.message.from_user.id

    # Connect to the SQLite database
    conn = get_connection()
    cursor = conn.cursor()

    # Query to fetch all the user's spendings
    cursor.execute("""
        SELECT description, amount, currency, category, date
        FROM spendings
        WHERE user_id = ?
    """, (user_id,))

    # Fetch all the records
    spendings = cursor.fetchall()

    # Create a CSV file in memory
    output = io.StringIO()
    csv_writer = csv.writer(output)

    # Write headers
    csv_writer.writerow(['Description', 'Amount', 'Currency', 'Category', 'Date'])

    # Write each spending record
    for spending in spendings:
        csv_writer.writerow(spending)

    # Reset pointer to the beginning of the file
    output.seek(0)

    # Send the file back to the user
    await update.message.reply_document(document=output, filename="spendings.csv")

    # Close the database connection
    conn.close()
