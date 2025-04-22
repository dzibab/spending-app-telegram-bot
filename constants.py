DEFAULT_CURRENCIES = ["USD", "EUR", "CNY"]
DEFAULT_CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Utilities",
    "Health",
    "Entertainment",
    "Shopping",
    "Travel",
]

BOT_COMMANDS = {
    "start": {
        "command": "start",
        "description": "Start the bot",
        "help": "Start the bot and initialize your account",
        "frequency": "high",
        "category": "essential",
    },
    "add_spending": {
        "command": "add_spending",
        "description": "Add a spending",
        "help": "Record a new expense",
        "frequency": "high",
        "category": "essential",
    },
    "list": {
        "command": "list",
        "description": "List spendings",
        "help": "View and manage your spendings, including deletion",
        "frequency": "high",
        "category": "essential",
    },
    "search_spending": {
        "command": "search",
        "description": "Search spendings",
        "help": "Search spendings by amount or description",
        "frequency": "high",
        "category": "essential",
    },
    "report": {
        "command": "report",
        "description": "View spending reports",
        "help": "View spending reports and charts",
        "frequency": "high",
        "category": "essential",
    },
    "settings": {
        "command": "settings",
        "description": "Manage settings and utilities",
        "help": "Access less frequently used commands and settings",
        "frequency": "medium",
        "category": "essential",
    },
    "add_category": {
        "command": "add_category",
        "description": "Add a category",
        "help": "Add a new spending category",
        "frequency": "low",
        "category": "category_settings",
    },
    # Removed "remove_category" command as it's now handled in the settings menu
    "add_currency": {
        "command": "add_currency",
        "description": "Add a currency",
        "help": "Add a new currency",
        "frequency": "low",
        "category": "currency_settings",
    },
    # Removed "main_currency" command as it's now handled in the settings menu
    "export": {
        "command": "export",
        "description": "Export spendings",
        "help": "Download your spendings as a CSV file",
        "frequency": "low",
        "category": "data_management",
    },
    "import": {
        "command": "import",
        "description": "Import spendings",
        "help": "Upload a CSV file with spendings to import",
        "frequency": "low",
        "category": "data_management",
    },
}

# Pagination settings
ITEMS_PER_PAGE = 5  # Number of items to show per page in list and remove views

# Generate usage instructions from commands
BOT_USAGE_INSTRUCTIONS = "\n".join(
    f"Use /{cmd_info['command']}: {cmd_info['help']}."
    for cmd_info in BOT_COMMANDS.values()
    if cmd_info["command"] != "start"  # Skip start command in instructions
)
