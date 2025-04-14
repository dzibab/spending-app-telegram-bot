import sqlite3


def get_connection():
    return sqlite3.connect("spendings.db")


def init_db():
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
