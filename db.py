import sqlite3

from constants import DEFAULT_CURRENCIES, DEFAULT_CATEGORIES
from utils.logging import logger


def get_connection():
    logger.debug("Opening new database connection")
    return sqlite3.connect("spendings.db")


def create_tables() -> None:
    logger.info("Initializing database tables")
    try:
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
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def initialize_user_currencies(user_id: int) -> None:
    logger.info(f"Initializing default currencies for user {user_id}")
    try:
        with get_connection() as conn:
            # Check if the user already has currencies initialized
            currencies_exist = conn.execute(
                "SELECT 1 FROM currencies WHERE user_id = ? LIMIT 1;", (user_id,)
            ).fetchone()

            # Skip initialization if currencies exist
            if currencies_exist:
                logger.debug(f"User {user_id} already has currencies initialized")
                return

            # Initialize default currencies
            default_currencies = [(user_id, currency) for currency in DEFAULT_CURRENCIES]
            conn.executemany("""
                INSERT OR IGNORE INTO currencies (user_id, currency_code)
                VALUES (?, ?);
            """, default_currencies)
            logger.info(f"Default currencies initialized for user {user_id}")
    except Exception as e:
        logger.error(f"Error initializing currencies for user {user_id}: {e}")
        raise


def initialize_user_categories(user_id: int) -> None:
    logger.info(f"Initializing default categories for user {user_id}")
    try:
        with get_connection() as conn:
            # Check if the user already has categories initialized
            categories_exist = conn.execute(
                "SELECT 1 FROM categories WHERE user_id = ? LIMIT 1;", (user_id,)
            ).fetchone()

            # Skip initialization if categories exist
            if categories_exist:
                logger.debug(f"User {user_id} already has categories initialized")
                return

            # Initialize default categories
            default_categories = [(user_id, category) for category in DEFAULT_CATEGORIES]
            conn.executemany("""
                INSERT OR IGNORE INTO categories (user_id, category_name)
                VALUES (?, ?);
            """, default_categories)
            logger.info(f"Default categories initialized for user {user_id}")
    except Exception as e:
        logger.error(f"Error initializing categories for user {user_id}: {e}")
        raise


def initialize_user_defaults(user_id: int) -> None:
    logger.info(f"Initializing default settings for user {user_id}")
    try:
        initialize_user_currencies(user_id)
        initialize_user_categories(user_id)
        logger.info(f"Successfully initialized all defaults for user {user_id}")
    except Exception as e:
        logger.error(f"Error initializing defaults for user {user_id}: {e}")
        raise


def get_user_currencies(user_id: int) -> list:
    """Fetch the list of currencies for a user."""
    logger.debug(f"Fetching currencies for user {user_id}")
    try:
        with get_connection() as conn:
            currencies = [row[0] for row in conn.execute(
                "SELECT currency_code FROM currencies WHERE user_id = ?", (user_id,)
            ).fetchall()]
            logger.debug(f"Retrieved {len(currencies)} currencies for user {user_id}")
            return currencies
    except Exception as e:
        logger.error(f"Error fetching currencies for user {user_id}: {e}")
        return []


def get_user_categories(user_id: int) -> list:
    """Fetch the list of categories for a user."""
    logger.debug(f"Fetching categories for user {user_id}")
    try:
        with get_connection() as conn:
            categories = [row[0] for row in conn.execute(
                "SELECT category_name FROM categories WHERE user_id = ?", (user_id,)
            ).fetchall()]
            logger.debug(f"Retrieved {len(categories)} categories for user {user_id}")
            return categories
    except Exception as e:
        logger.error(f"Error fetching categories for user {user_id}: {e}")
        return []


def add_currency_to_user(user_id: int, currency: str) -> bool:
    """Add a new currency for a user."""
    logger.info(f"Adding currency {currency} for user {user_id}")
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO currencies (user_id, currency_code)
                VALUES (?, ?);
            """, (user_id, currency))
            logger.info(f"Currency {currency} added for user {user_id}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Currency {currency} already exists for user {user_id}")
        return False  # Currency already exists
    except Exception as e:
        logger.error(f"Error adding currency {currency} for user {user_id}: {e}")
        return False


def add_category_to_user(user_id: int, category: str) -> bool:
    """Add a new category for a user."""
    logger.info(f"Adding category {category} for user {user_id}")
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO categories (user_id, category_name)
                VALUES (?, ?);
            """, (user_id, category))
            logger.info(f"Category {category} added for user {user_id}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Category {category} already exists for user {user_id}")
        return False  # Category already exists
    except Exception as e:
        logger.error(f"Error adding category {category} for user {user_id}: {e}")
        return False


def remove_currency_from_user(user_id: int, currency: str) -> bool:
    """Remove a currency for a user."""
    logger.info(f"Removing currency {currency} for user {user_id}")
    try:
        with get_connection() as conn:
            conn.execute("""
                DELETE FROM currencies
                WHERE user_id = ? AND currency_code = ?;
            """, (user_id, currency))
            logger.info(f"Currency {currency} removed for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error removing currency {currency} for user {user_id}: {e}")
        return False


def remove_category_from_user(user_id: int, category: str) -> bool:
    """Remove a category for a user."""
    logger.info(f"Removing category {category} for user {user_id}")
    try:
        with get_connection() as conn:
            conn.execute("""
                DELETE FROM categories
                WHERE user_id = ? AND category_name = ?;
            """, (user_id, category))
            logger.info(f"Category {category} removed for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error removing category {category} for user {user_id}: {e}")
        return False


def get_user_main_currency(user_id: int) -> str:
    """Fetch the main currency for a user."""
    logger.debug(f"Fetching main currency for user {user_id}")
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT currency_code FROM main_currency WHERE user_id = ?", (user_id,)
            ).fetchone()
            main_currency = row[0] if row else None
            logger.debug(f"Main currency for user {user_id}: {main_currency}")
            return main_currency
    except Exception as e:
        logger.error(f"Error fetching main currency for user {user_id}: {e}")
        return None


def set_user_main_currency(user_id: int, currency_code: str) -> None:
    """Set or update the main currency for a user."""
    logger.info(f"Setting main currency {currency_code} for user {user_id}")
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO main_currency (user_id, currency_code)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET currency_code = excluded.currency_code;
                """,
                (user_id, currency_code),
            )
            logger.info(f"Main currency {currency_code} set for user {user_id}")
    except Exception as e:
        logger.error(f"Error setting main currency {currency_code} for user {user_id}: {e}")
        raise


def get_unique_month_year_combinations(user_id: int):
    """Fetch unique month-year combinations for a user."""
    logger.debug(f"Fetching unique month-year combinations for user {user_id}")
    query = """
        SELECT DISTINCT strftime('%m', date) as month, strftime('%Y', date) as year
        FROM spendings
        WHERE user_id = ?
        ORDER BY year DESC, month DESC
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(query, (user_id,))
            combinations = cursor.fetchall()
            logger.debug(f"Retrieved {len(combinations)} month-year combinations for user {user_id}")
            return combinations
    except Exception as e:
        logger.error(f"Error fetching month-year combinations for user {user_id}: {e}")
        return []


def get_spending_data_for_month(user_id: int, year: str, month: str):
    """Fetch spending data for a specific month and year."""
    logger.debug(f"Fetching spending data for user {user_id} for year {year} and month {month}")
    query = """
        SELECT category, SUM(amount) as total, currency
        FROM spendings
        WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
        GROUP BY category, currency
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(query, (user_id, year, month))
            data = cursor.fetchall()
            logger.debug(f"Retrieved {len(data)} spending records for user {user_id} for year {year} and month {month}")
            return data
    except Exception as e:
        logger.error(f"Error fetching spending data for user {user_id} for year {year} and month {month}: {e}")
        return []


def get_spending_totals_by_category(user_id: int, year: str, month: str):
    """
    Fetches the total spending grouped by category for a specific user, year, and month.
    Returns category, total amount, and currency for proper conversion.
    """
    logger.debug(f"Fetching spending totals by category for user {user_id} for year {year} and month {month}")
    try:
        with get_connection() as conn:
            totals = conn.execute(
                """
                SELECT category, SUM(amount) as total, currency
                FROM spendings
                WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
                GROUP BY category, currency
                """, (user_id, year, month)
            ).fetchall()
            logger.debug(f"Retrieved {len(totals)} spending totals for user {user_id} for year {year} and month {month}")
            return totals
    except Exception as e:
        logger.error(f"Error fetching spending totals for user {user_id} for year {year} and month {month}: {e}")
        return []


def add_spending(user_id: int, description: str, amount: float, currency: str, category: str, spend_date: str) -> int:
    """Add a new spending record and return its ID."""
    logger.info(f"Adding spending for user {user_id}: {description}, {amount} {currency}, category {category}, date {spend_date}")
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO spendings (user_id, description, amount, currency, category, date) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, description, amount, currency, category, spend_date)
            )
            spending_id = cursor.lastrowid
            logger.info(f"Spending added with ID {spending_id} for user {user_id}")
            return spending_id
    except Exception as e:
        logger.error(f"Error adding spending for user {user_id}: {e}")
        return None


def remove_spending(user_id: int, spending_id: int) -> bool:
    """Remove a spending record. Returns True if successful."""
    logger.info(f"Removing spending with ID {spending_id} for user {user_id}")
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM spendings WHERE id = ? AND user_id = ?",
                (spending_id, user_id)
            )
            success = cursor.rowcount > 0
            if success:
                logger.info(f"Spending with ID {spending_id} removed for user {user_id}")
            else:
                logger.warning(f"Spending with ID {spending_id} not found for user {user_id}")
            return success
    except Exception as e:
        logger.error(f"Error removing spending with ID {spending_id} for user {user_id}: {e}")
        return False


def get_recent_spendings(user_id: int, limit: int = 10) -> list:
    """Get recent spendings for a user."""
    logger.debug(f"Fetching recent spendings for user {user_id} with limit {limit}")
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
                SELECT description, amount, currency, category, date
                FROM spendings
                WHERE user_id = ?
                ORDER BY date DESC, id DESC
                LIMIT ?
            """, (user_id, limit))
            spendings = cursor.fetchall()
            logger.debug(f"Retrieved {len(spendings)} recent spendings for user {user_id}")
            return spendings
    except Exception as e:
        logger.error(f"Error fetching recent spendings for user {user_id}: {e}")
        return []


def get_total_spendings(user_id: int, category: str = None) -> list:
    """Get total spendings grouped by currency, optionally filtered by category."""
    logger.debug(f"Fetching total spendings for user {user_id} with category filter: {category}")
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

    try:
        with get_connection() as conn:
            cursor = conn.execute(query, params)
            totals = cursor.fetchall()
            logger.debug(f"Retrieved {len(totals)} total spendings for user {user_id}")
            return totals
    except Exception as e:
        logger.error(f"Error fetching total spendings for user {user_id}: {e}")
        return []


def export_all_spendings(user_id: int) -> list:
    """Export all spendings for a user."""
    logger.debug(f"Exporting all spendings for user {user_id}")
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
                SELECT description, amount, currency, category, date
                FROM spendings
                WHERE user_id = ?
            """, (user_id,))
            spendings = cursor.fetchall()
            logger.debug(f"Exported {len(spendings)} spendings for user {user_id}")
            return spendings
    except Exception as e:
        logger.error(f"Error exporting spendings for user {user_id}: {e}")
        return []
