# Spending App Telegram Bot

A Telegram bot that helps you track and manage your spending across multiple currencies.

## Features

- Track your spending by interacting with the bot on Telegram
- Add, view, and delete expenses with simple commands
- Categorize expenses for better organization
- Support for multiple currencies with automatic exchange rate conversion
- Generate spending reports and visual charts to analyze your spending habits
- Export your spending data as CSV for further analysis
- Import spending data from CSV files
- Archive and restore currencies while preserving historical data
- Customizable settings and preferences

## How to Use

1. Start the bot on Telegram by searching for its username and clicking "Start."
2. Available commands:
    - `/start`: Start the bot and initialize your account.
    - `/add_spending`: Record a new expense.
    - `/list`: View your spendings with pagination, see details, and delete them.
    - `/search`: Search for specific spendings by description or amount.
    - `/report`: View spending reports and charts.
    - `/settings`: Access all settings and utilities.
    - `/export`: Download your spendings as a CSV file.
    - `/import`: Upload a CSV file to import multiple spendings at once.

3. Settings menu provides access to:
    - Set your main currency for reports
    - Add new spending categories
    - Remove existing categories
    - Add new currencies
    - Archive currencies you no longer use
    - Restore previously archived currencies

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

## Development Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/dzibab/spending-app-telegram-bot.git
    cd spending-app-telegram-bot
    ```

2. Create a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. Create a `.env` file with your configuration:
    ```
    BOT_TOKEN=your_telegram_bot_token
    EXCHANGE_API_KEY=your_exchange_api_key
    ```

4. Run database migrations:
    ```bash
    alembic upgrade head
    ```

5. Start the bot:
    ```bash
    python bot.py
    ```

## Notes

- Ensure you have Docker and Docker Compose installed on your system for Docker deployment.
- Make sure to have a valid exchange rate API key for currency conversion features.
