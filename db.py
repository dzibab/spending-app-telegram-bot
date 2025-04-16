import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple

from constants import DEFAULT_CURRENCIES, DEFAULT_CATEGORIES
from utils.logging import logger


@dataclass
class Spending:
    """Represents a spending record."""
    id: Optional[int]
    user_id: int
    description: str
    amount: float
    currency: str
    category: str
    date: str

    @classmethod
    def from_row(cls, row: tuple) -> 'Spending':
        """Create a Spending instance from a database row."""
        return cls(
            id=row[0], user_id=row[1], description=row[2],
            amount=row[3], currency=row[4], category=row[5], date=row[6]
        )


class Database:
    """Handles database operations for the spending tracker bot."""

    def __init__(self, db_path: str = "spendings.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._connection = None

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        if not self._connection:
            logger.debug("Opening new database connection")
            self._connection = sqlite3.connect(self.db_path)
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        logger.info("Initializing database tables")
        try:
            with self.get_connection() as conn:
                # Create spendings table with index on user_id and date
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS spendings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        description TEXT,
                        amount REAL NOT NULL,
                        currency TEXT NOT NULL,
                        category TEXT NOT NULL,
                        date TEXT NOT NULL,
                        FOREIGN KEY (user_id, currency) REFERENCES currencies (user_id, currency_code),
                        FOREIGN KEY (user_id, category) REFERENCES categories (user_id, category_name)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_spendings_user_date ON spendings(user_id, date);")

                # Create currencies table with composite primary key
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS currencies (
                        user_id INTEGER NOT NULL,
                        currency_code TEXT NOT NULL,
                        PRIMARY KEY (user_id, currency_code)
                    );
                """)

                # Create categories table with composite primary key
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        user_id INTEGER NOT NULL,
                        category_name TEXT NOT NULL,
                        PRIMARY KEY (user_id, category_name)
                    );
                """)

                # Create main_currency table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS main_currency (
                        user_id INTEGER PRIMARY KEY,
                        currency_code TEXT NOT NULL
                    );
                """)

            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def initialize_user_currencies(self, user_id: int) -> None:
        """Initialize default currencies for a user."""
        logger.info(f"Initializing default currencies for user {user_id}")
        try:
            with self.get_connection() as conn:
                # Check if user already has currencies
                currencies_exist = conn.execute(
                    "SELECT 1 FROM currencies WHERE user_id = ? LIMIT 1;",
                    (user_id,)
                ).fetchone()

                if currencies_exist:
                    logger.debug(f"User {user_id} already has currencies initialized")
                    return

                # Initialize default currencies
                default_currencies = [(user_id, currency) for currency in DEFAULT_CURRENCIES]
                conn.executemany(
                    "INSERT INTO currencies (user_id, currency_code) VALUES (?, ?);",
                    default_currencies
                )
                logger.info(f"Default currencies initialized for user {user_id}")
        except Exception as e:
            logger.error(f"Error initializing currencies for user {user_id}: {e}")
            raise

    def initialize_user_categories(self, user_id: int) -> None:
        """Initialize default categories for a user."""
        logger.info(f"Initializing default categories for user {user_id}")
        try:
            with self.get_connection() as conn:
                # Check if user already has categories
                categories_exist = conn.execute(
                    "SELECT 1 FROM categories WHERE user_id = ? LIMIT 1;",
                    (user_id,)
                ).fetchone()

                if categories_exist:
                    logger.debug(f"User {user_id} already has categories initialized")
                    return

                # Initialize default categories
                default_categories = [(user_id, category) for category in DEFAULT_CATEGORIES]
                conn.executemany(
                    "INSERT INTO categories (user_id, category_name) VALUES (?, ?);",
                    default_categories
                )
                logger.info(f"Default categories initialized for user {user_id}")
        except Exception as e:
            logger.error(f"Error initializing categories for user {user_id}: {e}")
            raise

    def initialize_user_defaults(self, user_id: int) -> None:
        """Initialize default settings for a new user."""
        logger.info(f"Initializing default settings for user {user_id}")
        try:
            self.initialize_user_currencies(user_id)
            self.initialize_user_categories(user_id)
            logger.info(f"Successfully initialized all defaults for user {user_id}")
        except Exception as e:
            logger.error(f"Error initializing defaults for user {user_id}: {e}")
            raise

    def get_user_currencies(self, user_id: int) -> List[str]:
        """Get list of currencies for a user."""
        logger.debug(f"Fetching currencies for user {user_id}")
        try:
            with self.get_connection() as conn:
                currencies = [row[0] for row in conn.execute(
                    "SELECT currency_code FROM currencies WHERE user_id = ?",
                    (user_id,)
                ).fetchall()]
                logger.debug(f"Retrieved {len(currencies)} currencies for user {user_id}")
                return currencies
        except Exception as e:
            logger.error(f"Error fetching currencies for user {user_id}: {e}")
            return []

    def get_user_categories(self, user_id: int) -> List[str]:
        """Get list of categories for a user."""
        logger.debug(f"Fetching categories for user {user_id}")
        try:
            with self.get_connection() as conn:
                categories = [row[0] for row in conn.execute(
                    "SELECT category_name FROM categories WHERE user_id = ?",
                    (user_id,)
                ).fetchall()]
                logger.debug(f"Retrieved {len(categories)} categories for user {user_id}")
                return categories
        except Exception as e:
            logger.error(f"Error fetching categories for user {user_id}: {e}")
            return []

    def add_currency_to_user(self, user_id: int, currency: str) -> bool:
        """Add a new currency for a user."""
        logger.info(f"Adding currency {currency} for user {user_id}")
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO currencies (user_id, currency_code) VALUES (?, ?);",
                    (user_id, currency)
                )
                logger.info(f"Currency {currency} added for user {user_id}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Currency {currency} already exists for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding currency {currency} for user {user_id}: {e}")
            return False

    def add_category_to_user(self, user_id: int, category: str) -> bool:
        """Add a new category for a user."""
        logger.info(f"Adding category {category} for user {user_id}")
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO categories (user_id, category_name) VALUES (?, ?);",
                    (user_id, category)
                )
                logger.info(f"Category {category} added for user {user_id}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Category {category} already exists for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding category {category} for user {user_id}: {e}")
            return False

    def remove_currency_from_user(self, user_id: int, currency: str) -> bool:
        """Remove a currency from a user."""
        logger.info(f"Removing currency {currency} for user {user_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM currencies WHERE user_id = ? AND currency_code = ?;",
                    (user_id, currency)
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Currency {currency} removed for user {user_id}")
                else:
                    logger.warning(f"Currency {currency} not found for user {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error removing currency {currency} for user {user_id}: {e}")
            return False

    def remove_category_from_user(self, user_id: int, category: str) -> bool:
        """Remove a category from a user."""
        logger.info(f"Removing category {category} for user {user_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM categories WHERE user_id = ? AND category_name = ?;",
                    (user_id, category)
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Category {category} removed for user {user_id}")
                else:
                    logger.warning(f"Category {category} not found for user {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error removing category {category} for user {user_id}: {e}")
            return False

    def get_user_main_currency(self, user_id: int) -> Optional[str]:
        """Get main currency for a user."""
        logger.debug(f"Fetching main currency for user {user_id}")
        try:
            with self.get_connection() as conn:
                row = conn.execute(
                    "SELECT currency_code FROM main_currency WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                main_currency = row[0] if row else None
                logger.debug(f"Main currency for user {user_id}: {main_currency}")
                return main_currency
        except Exception as e:
            logger.error(f"Error fetching main currency for user {user_id}: {e}")
            return None

    def set_user_main_currency(self, user_id: int, currency_code: str) -> None:
        """Set main currency for a user."""
        logger.info(f"Setting main currency {currency_code} for user {user_id}")
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO main_currency (user_id, currency_code)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET currency_code = excluded.currency_code;
                """, (user_id, currency_code))
                logger.info(f"Main currency {currency_code} set for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting main currency {currency_code} for user {user_id}: {e}")
            raise

    def get_unique_month_year_combinations(self, user_id: int) -> List[Tuple[str, str]]:
        """Get unique month-year combinations for a user's spendings."""
        logger.debug(f"Fetching unique month-year combinations for user {user_id}")
        query = """
            SELECT DISTINCT strftime('%m', date) as month, strftime('%Y', date) as year
            FROM spendings
            WHERE user_id = ?
            ORDER BY year DESC, month DESC
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (user_id,))
                combinations = cursor.fetchall()
                logger.debug(f"Retrieved {len(combinations)} month-year combinations for user {user_id}")
                return combinations
        except Exception as e:
            logger.error(f"Error fetching month-year combinations for user {user_id}: {e}")
            return []

    def get_spending_data_for_month(
        self, user_id: int, year: str, month: str
    ) -> List[Tuple[str, float, str]]:
        """Get spending data for a specific month."""
        logger.debug(f"Fetching spending data for user {user_id} for {month}/{year}")
        query = """
            SELECT category, SUM(amount) as total, currency
            FROM spendings
            WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
            GROUP BY category, currency
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, (user_id, year, month))
                data = cursor.fetchall()
                logger.debug(f"Retrieved {len(data)} spending records")
                return data
        except Exception as e:
            logger.error(f"Error fetching spending data: {e}")
            return []

    def get_spending_totals_by_category(
        self, user_id: int, year: str, month: str
    ) -> List[Tuple[str, float, str]]:
        """Get spending totals grouped by category for a specific month."""
        logger.debug(f"Fetching spending totals by category for user {user_id} for {month}/{year}")
        try:
            with self.get_connection() as conn:
                totals = conn.execute("""
                    SELECT category, SUM(amount) as total, currency
                    FROM spendings
                    WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
                    GROUP BY category, currency
                """, (user_id, year, month)).fetchall()
                logger.debug(f"Retrieved {len(totals)} spending totals")
                return totals
        except Exception as e:
            logger.error(f"Error fetching spending totals: {e}")
            return []

    def add_spending(
        self, user_id: int, description: str, amount: float,
        currency: str, category: str, spend_date: str
    ) -> Optional[int]:
        """Add a new spending record."""
        logger.info(f"Adding spending for user {user_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO spendings (
                        user_id, description, amount, currency, category, date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, description, amount, currency, category, spend_date))
                spending_id = cursor.lastrowid
                logger.info(f"Spending added with ID {spending_id}")
                return spending_id
        except Exception as e:
            logger.error(f"Error adding spending: {e}")
            return None

    def remove_spending(self, user_id: int, spending_id: int) -> bool:
        """Remove a spending record."""
        logger.info(f"Removing spending with ID {spending_id} for user {user_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM spendings WHERE id = ? AND user_id = ?",
                    (spending_id, user_id)
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info("Spending removed successfully")
                else:
                    logger.warning("Spending not found")
                return success
        except Exception as e:
            logger.error(f"Error removing spending: {e}")
            return False

    def get_recent_spendings(
        self, user_id: int, limit: int = 10
    ) -> List[Tuple[str, float, str, str, str]]:
        """Get recent spendings for a user."""
        logger.debug(f"Fetching recent spendings for user {user_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT description, amount, currency, category, date
                    FROM spendings
                    WHERE user_id = ?
                    ORDER BY date DESC, id DESC
                    LIMIT ?
                """, (user_id, limit))
                spendings = cursor.fetchall()
                logger.debug(f"Retrieved {len(spendings)} recent spendings")
                return spendings
        except Exception as e:
            logger.error(f"Error fetching recent spendings: {e}")
            return []

    def get_total_spendings(
        self, user_id: int, category: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Get total spendings grouped by currency."""
        logger.debug(f"Fetching total spendings for user {user_id}")
        query = "SELECT currency, SUM(amount) FROM spendings WHERE user_id = ?"
        params = [user_id]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY currency"

        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                totals = cursor.fetchall()
                logger.debug(f"Retrieved {len(totals)} total spendings")
                return totals
        except Exception as e:
            logger.error(f"Error fetching total spendings: {e}")
            return []

    def export_all_spendings(
        self, user_id: int
    ) -> List[Tuple[str, float, str, str, str]]:
        """Export all spendings for a user."""
        logger.debug(f"Exporting all spendings for user {user_id}")
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT description, amount, currency, category, date
                    FROM spendings
                    WHERE user_id = ?
                    ORDER BY date DESC, id DESC
                """, (user_id,))
                spendings = cursor.fetchall()
                logger.debug(f"Exported {len(spendings)} spendings")
                return spendings
        except Exception as e:
            logger.error(f"Error exporting spendings: {e}")
            return []


# Create global database instance
db = Database()
