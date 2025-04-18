# spending-app-telegram-bot
## Features

- Track your spending by interacting with the bot on Telegram.
- Add, view, and delete expenses with simple commands.
- Get a summary of your spending categorized by type.
- Export your spending data for further analysis.

## How to Use

1. Start the bot on Telegram by searching for its username and clicking "Start."
2. Available commands:
    - `/start`: Start the bot and initialize your account.
    - `/add_spending`: Record a new expense.
    - `/list`: View your spendings with pagination, see details, and delete them.
    - `/search`: Search for specific spendings by description or amount.
    - `/report`: View spending reports and charts.
    - `/export`: Download your spendings as a CSV file.
    - `/main_currency`: Set your main currency for reports.
    - `/add_category`: Add a new spending category.
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
    EXCHANGE_API_KEY=your_exchange_api_key
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
