DEFAULT_CURRENCIES = ["USD", "EUR", "CNY"]
DEFAULT_CATEGORIES = [
    "Food", "Transport", "Housing", "Utilities", "Health", "Entertainment", "Shopping", "Travel"
]

BOT_COMMANDS = {
    "start": {
        "command": "start",
        "description": "Start the bot",
        "help": "Start the bot and initialize your account"
    },
    "add_spending": {
        "command": "add_spending",
        "description": "Add a spending",
        "help": "Record a new expense"
    },
    "search_spending": {
        "command": "search",
        "description": "Search spendings",
        "help": "Search spendings by amount or description"
    },
    "add_category": {
        "command": "add_category",
        "description": "Add a category",
        "help": "Add a new spending category"
    },
    "remove_category": {
        "command": "remove_category",
        "description": "Remove a category",
        "help": "Remove an existing category"
    },
    "add_currency": {
        "command": "add_currency",
        "description": "Add a currency",
        "help": "Add a new currency"
    },
    "remove_currency": {
        "command": "remove_currency",
        "description": "Remove a currency",
        "help": "Remove an existing currency"
    },
    "list": {
        "command": "list",
        "description": "List spendings",
        "help": "View and manage your spendings, including deletion"
    },
    "report": {
        "command": "report",
        "description": "View spending reports",
        "help": "View spending reports and charts"
    },
    "export": {
        "command": "export",
        "description": "Export spendings",
        "help": "Download your spendings as a CSV file"
    },
    "main_currency": {
        "command": "main_currency",
        "description": "Choose main currency",
        "help": "Set your main currency for reports"
    }
}

# Pagination settings
ITEMS_PER_PAGE = 5  # Number of items to show per page in list and remove views

# Generate usage instructions from commands
BOT_USAGE_INSTRUCTIONS = "\n".join(
    f"Use /{cmd_info['command']}: {cmd_info['help']}."
    for cmd_info in BOT_COMMANDS.values()
    if cmd_info['command'] != 'start'  # Skip start command in instructions
)
