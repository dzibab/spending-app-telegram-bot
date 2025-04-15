import sqlite3

from constants import DEFAULT_CURRENCIES, DEFAULT_CATEGORIES
from utils.logging import logger


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
                currency_code TEXT,
                UNIQUE(user_id, currency_code) ON CONFLICT IGNORE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category_name TEXT,
                UNIQUE(user_id, category_name) ON CONFLICT IGNORE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS main_currency (
                user_id INTEGER PRIMARY KEY,
                currency_code TEXT
            );
        """)


def initialize_user_currencies(user_id: int) -> None:
    with get_connection() as conn:
        # Check if the user already has currencies initialized
        currencies_exist = conn.execute(
            "SELECT 1 FROM currencies WHERE user_id = ? LIMIT 1;", (user_id,)
        ).fetchone()

        # Skip initialization if currencies exist
        if currencies_exist:
            return

        # Initialize default currencies
        default_currencies = [(user_id, currency) for currency in DEFAULT_CURRENCIES]
        conn.executemany("""
            INSERT OR IGNORE INTO currencies (user_id, currency_code)
            VALUES (?, ?);
        """, default_currencies)


def initialize_user_categories(user_id: int) -> None:
    with get_connection() as conn:
        # Check if the user already has categories initialized
        categories_exist = conn.execute(
            "SELECT 1 FROM categories WHERE user_id = ? LIMIT 1;", (user_id,)
        ).fetchone()

        # Skip initialization if categories exist
        if categories_exist:
            return

        # Initialize default categories
        default_categories = [(user_id, category) for category in DEFAULT_CATEGORIES]
        conn.executemany("""
            INSERT OR IGNORE INTO categories (user_id, category_name)
            VALUES (?, ?);
        """, default_categories)


def initialize_user_defaults(user_id: int) -> None:
    initialize_user_currencies(user_id)
    initialize_user_categories(user_id)


def get_user_currencies(user_id: int) -> list:
    """Fetch the list of currencies for a user."""
    with get_connection() as conn:
        try:
            currencies = [row[0] for row in conn.execute(
                "SELECT currency_code FROM currencies WHERE user_id = ?", (user_id,)
            ).fetchall()]
            logger.debug(f"Fetched currencies for user {user_id}: {currencies}")
            return currencies
        except Exception as e:
            logger.error(f"Error fetching currencies for user {user_id}: {e}")
            return []


def get_user_categories(user_id: int) -> list:
    """Fetch the list of categories for a user."""
    with get_connection() as conn:
        return [row[0] for row in conn.execute(
            "SELECT category_name FROM categories WHERE user_id = ?", (user_id,)
        ).fetchall()]


def add_currency_to_user(user_id: int, currency: str) -> bool:
    """Add a new currency for a user."""
    with get_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO currencies (user_id, currency_code)
                VALUES (?, ?);
            """, (user_id, currency))
            logger.debug(f"Added currency {currency} for user {user_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Currency {currency} already exists for user {user_id}")
            return False  # Currency already exists
        except Exception as e:
            logger.error(f"Error adding currency {currency} for user {user_id}: {e}")
            return False


def add_category_to_user(user_id: int, category: str) -> bool:
    """Add a new category for a user."""
    with get_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO categories (user_id, category_name)
                VALUES (?, ?);
            """, (user_id, category))
            logger.debug(f"Added category {category} for user {user_id}")
            return True
        except sqlite3.IntegrityError:
            return False  # Category already exists
        except Exception as e:
            logger.error(f"Error adding category {category} for user {user_id}: {e}")
            return False


def remove_currency_from_user(user_id: int, currency: str) -> bool:
    """Remove a currency for a user."""
    with get_connection() as conn:
        try:
            conn.execute("""
                DELETE FROM currencies
                WHERE user_id = ? AND currency_code = ?;
            """, (user_id, currency))
            logger.debug(f"Removed currency {currency} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing currency {currency} for user {user_id}: {e}")
            return False


def remove_category_from_user(user_id: int, category: str) -> bool:
    """Remove a category for a user."""
    with get_connection() as conn:
        try:
            conn.execute("""
                DELETE FROM categories
                WHERE user_id = ? AND category_name = ?;
            """, (user_id, category))
            logger.debug(f"Removed category {category} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing category {category} for user {user_id}: {e}")
            return False


def get_user_main_currency(user_id: int) -> str:
    """Fetch the main currency for a user."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT currency_code FROM main_currency WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row else None


def get_unique_month_year_combinations(user_id: int):
    """Fetch unique month-year combinations for a user."""
    query = """
        SELECT DISTINCT strftime('%m', date) as month, strftime('%Y', date) as year
        FROM spendings
        WHERE user_id = ?
        ORDER BY year DESC, month DESC
    """
    with get_connection() as conn:
        cursor = conn.execute(query, (user_id,))
        return cursor.fetchall()


def get_spending_data_for_month(user_id: int, year: str, month: str):
    """Fetch spending data for a specific month and year."""
    query = """
        SELECT category, SUM(amount) as total, currency
        FROM spendings
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category, currency
    """
    with get_connection() as conn:
        cursor = conn.execute(query, (user_id, year, month))
        return cursor.fetchall()


def get_spending_totals_by_category(user_id: int, year: str, month: str):
    """
    Fetches the total spending grouped by category for a specific user, year, and month.

    Args:
        user_id (int): The ID of the user.
        year (str): The year in YYYY format.
        month (str): The month in MM format.

    Returns:
        list: A list of tuples containing category and total spending.
    """
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT category, SUM(amount) as total
            FROM spendings
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            GROUP BY category
            """, (user_id, year, month)
        ).fetchall()


def add_spending(user_id: int, description: str, amount: float, currency: str, category: str, spend_date: str) -> int:
    """Add a new spending record and return its ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO spendings (user_id, description, amount, currency, category, date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, description, amount, currency, category, spend_date)
        )
        return cursor.lastrowid


def remove_spending(user_id: int, spending_id: int) -> bool:
    """Remove a spending record. Returns True if successful."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM spendings WHERE id = ? AND user_id = ?",
            (spending_id, user_id)
        )
        return cursor.rowcount > 0


def get_recent_spendings(user_id: int, limit: int = 10) -> list:
    """Get recent spendings for a user."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT description, amount, currency, category, date
            FROM spendings
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()


def get_total_spendings(user_id: int, category: str = None) -> list:
    """Get total spendings grouped by currency, optionally filtered by category."""
    query = """
        SELECT currency, SUM(amount)
        FROM spendings
        WHERE user_id = ?
    """
    params = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY currency"

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def export_all_spendings(user_id: int) -> list:
    """Export all spendings for a user."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT description, amount, currency, category, date
            FROM spendings
            WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchall()
