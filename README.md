# spending-app-telegram-bot
## Features

- Track your spending by interacting with the bot on Telegram.
- Add, view, and delete expenses with simple commands.
- Get a summary of your spending categorized by type.
- Export your spending data for further analysis.

## How to Use

1. Start the bot on Telegram by searching for its username and clicking "Start."
2. Use the following commands to interact with the bot:
    - `/add_spending`: Add a new expense.
    - `/remove_spending <id>`: Remove and expense.
    - `/list`: View your recent expenses.
    - `/total`: Get a summary of your spending.
    - `/export`: Export your spending data.
    - `/main_currency`: Set your main currency.
    - `/add_category`: Add a new category.
    - `/remove_category`: Remove an existing category.
    - `/add_currency`: Add a new currency.
    - `/remove_currency`: Remove an existing currency.

## Deployment with Docker Compose

1. Clone the repository:
    ```bash
    git clone https://github.com/dzibab/spending-app-telegram-bot.git
    cd spending-app-telegram-bot
    ```

2. Create a `.env` file in the project root and add the following environment variables:
    ```
    BOT_TOKEN=your_telegram_bot_token
    ```

3. Build and start the application using Docker Compose:
    ```bash
    docker compose up --build
    ```

4. The bot will now be running and ready to use on Telegram.

5. To stop the application, use:
    ```bash
    docker compose down
    ```

## Notes

- Ensure you have Docker and Docker Compose installed on your system.
