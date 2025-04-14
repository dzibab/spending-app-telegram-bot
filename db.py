import sqlite3


from constants import DEFAULT_CURRENCIES, DEFAULT_CATEGORIES


def get_connection():
    return sqlite3.connect("spendings.db")


def create_tables() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spendings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                description TEXT,
                amount REAL,
                currency TEXT,
                category TEXT,
                date TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS currencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                currency_code TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category_name TEXT
            );
        """)


def populate_default_values(user_id: int) -> None:
    default_currencies = [(user_id, currency) for currency in DEFAULT_CURRENCIES]
    default_categories = [(user_id, category) for category in DEFAULT_CATEGORIES]

    with get_connection() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO currencies (user_id, currency_code)
            VALUES (?, ?);
        """, default_currencies)
        conn.executemany("""
            INSERT OR IGNORE INTO categories (user_id, category_name)
            VALUES (?, ?);
        """, default_categories)
