import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Optional, Tuple

import aiosqlite

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
        self._connection_lock = asyncio.Lock()

    async def get_connection(self) -> aiosqlite.Connection:
        """Get a database connection asynchronously."""
        async with self._connection_lock:
            if not self._connection:
                logger.debug("Opening new async database connection")
                self._connection = await aiosqlite.connect(self.db_path)
                # Enable foreign keys
                await self._connection.execute("PRAGMA foreign_keys = ON")
                # Make aiosqlite return rows as Row objects accessible by column name
                self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def close(self) -> None:
        """Close the database connection asynchronously."""
        async with self._connection_lock:
            if self._connection:
                await self._connection.close()
                self._connection = None
                logger.debug("Closed database connection")

    @asynccontextmanager
    async def connection(self):
        """Async context manager for database connections."""
        conn = await self.get_connection()
        try:
            async with conn.cursor() as cursor:
                yield cursor
        finally:
            pass  # Connection will be kept in the pool

    @asynccontextmanager
    async def transaction(self):
        """Async context manager for database transactions."""
        conn = await self.get_connection()
        await conn.execute("BEGIN")
        try:
            async with conn.cursor() as cursor:
                yield cursor
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    async def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        logger.info("Initializing database tables")
        try:
            async with self.connection() as cursor:
                # Create spendings table with index on user_id and date
                await cursor.execute("""
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
                await cursor.execute("CREATE INDEX IF NOT EXISTS idx_spendings_user_date ON spendings(user_id, date);")

                # Create currencies table with composite primary key
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS currencies (
                        user_id INTEGER NOT NULL,
                        currency_code TEXT NOT NULL,
                        PRIMARY KEY (user_id, currency_code)
                    );
                """)

                # Create categories table with composite primary key
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        user_id INTEGER NOT NULL,
                        category_name TEXT NOT NULL,
                        PRIMARY KEY (user_id, category_name)
                    );
                """)

                # Create main_currency table
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS main_currency (
                        user_id INTEGER PRIMARY KEY,
                        currency_code TEXT NOT NULL
                    );
                """)

            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    async def initialize_user_currencies(self, user_id: int) -> None:
        """Initialize default currencies for a user."""
        logger.info(f"Initializing default currencies for user {user_id}")
        try:
            async with self.transaction() as cursor:
                # Check if user already has currencies
                await cursor.execute(
                    "SELECT 1 FROM currencies WHERE user_id = ? LIMIT 1;",
                    (user_id,)
                )
                currencies_exist = await cursor.fetchone()

                if currencies_exist:
                    logger.debug(f"User {user_id} already has currencies initialized")
                    return

                # Initialize default currencies
                default_currencies = [(user_id, currency) for currency in DEFAULT_CURRENCIES]
                await cursor.executemany(
                    "INSERT INTO currencies (user_id, currency_code) VALUES (?, ?);",
                    default_currencies
                )
                logger.info(f"Default currencies initialized for user {user_id}")
        except Exception as e:
            logger.error(f"Error initializing currencies for user {user_id}: {e}")
            raise

    async def initialize_user_categories(self, user_id: int) -> None:
        """Initialize default categories for a user."""
        logger.info(f"Initializing default categories for user {user_id}")
        try:
            async with self.transaction() as cursor:
                # Check if user already has categories
                await cursor.execute(
                    "SELECT 1 FROM categories WHERE user_id = ? LIMIT 1;",
                    (user_id,)
                )
                categories_exist = await cursor.fetchone()

                if categories_exist:
                    logger.debug(f"User {user_id} already has categories initialized")
                    return

                # Initialize default categories
                default_categories = [(user_id, category) for category in DEFAULT_CATEGORIES]
                await cursor.executemany(
                    "INSERT INTO categories (user_id, category_name) VALUES (?, ?);",
                    default_categories
                )
                logger.info(f"Default categories initialized for user {user_id}")
        except Exception as e:
            logger.error(f"Error initializing categories for user {user_id}: {e}")
            raise

    async def initialize_user_defaults(self, user_id: int) -> None:
        """Initialize default settings for a new user."""
        logger.info(f"Initializing default settings for user {user_id}")
        try:
            await self.initialize_user_currencies(user_id)
            await self.initialize_user_categories(user_id)
            logger.info(f"Successfully initialized all defaults for user {user_id}")
        except Exception as e:
            logger.error(f"Error initializing defaults for user {user_id}: {e}")
            raise

    async def get_user_currencies(self, user_id: int) -> List[str]:
        """Get list of currencies for a user."""
        logger.debug(f"Fetching currencies for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT currency_code FROM currencies WHERE user_id = ?",
                    (user_id,)
                )
                rows = await cursor.fetchall()
                currencies = [row[0] for row in rows]
                logger.debug(f"Retrieved {len(currencies)} currencies for user {user_id}")
                return currencies
        except Exception as e:
            logger.error(f"Error fetching currencies for user {user_id}: {e}")
            return []

    async def get_user_categories(self, user_id: int) -> List[str]:
        """Get list of categories for a user."""
        logger.debug(f"Fetching categories for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT category_name FROM categories WHERE user_id = ?",
                    (user_id,)
                )
                rows = await cursor.fetchall()
                categories = [row[0] for row in rows]
                logger.debug(f"Retrieved {len(categories)} categories for user {user_id}")
                return categories
        except Exception as e:
            logger.error(f"Error fetching categories for user {user_id}: {e}")
            return []

    async def add_currency_to_user(self, user_id: int, currency: str) -> bool:
        """Add a new currency for a user."""
        logger.info(f"Adding currency {currency} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "INSERT INTO currencies (user_id, currency_code) VALUES (?, ?);",
                    (user_id, currency)
                )
                logger.info(f"Currency {currency} added for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error adding currency {currency} for user {user_id}: {e}")
            return False

    async def add_category_to_user(self, user_id: int, category: str) -> bool:
        """Add a new category for a user."""
        logger.info(f"Adding category {category} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "INSERT INTO categories (user_id, category_name) VALUES (?, ?);",
                    (user_id, category)
                )
                logger.info(f"Category {category} added for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error adding category {category} for user {user_id}: {e}")
            return False

    async def remove_currency_from_user(self, user_id: int, currency: str) -> bool:
        """Remove a currency from a user."""
        logger.info(f"Removing currency {currency} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "DELETE FROM currencies WHERE user_id = ? AND currency_code = ?;",
                    (user_id, currency)
                )
                # In aiosqlite, rowcount is available after execution
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Currency {currency} removed for user {user_id}")
                else:
                    logger.warning(f"Currency {currency} not found for user {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error removing currency {currency} for user {user_id}: {e}")
            return False

    async def remove_category_from_user(self, user_id: int, category: str) -> bool:
        """Remove a category from a user."""
        logger.info(f"Removing category {category} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
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

    async def get_user_main_currency(self, user_id: int) -> Optional[str]:
        """Get main currency for a user."""
        logger.debug(f"Fetching main currency for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT currency_code FROM main_currency WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                main_currency = row[0] if row else None
                logger.debug(f"Main currency for user {user_id}: {main_currency}")
                return main_currency
        except Exception as e:
            logger.error(f"Error fetching main currency for user {user_id}: {e}")
            return None

    async def set_user_main_currency(self, user_id: int, currency_code: str) -> None:
        """Set main currency for a user."""
        logger.info(f"Setting main currency {currency_code} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute("""
                    INSERT INTO main_currency (user_id, currency_code)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET currency_code = excluded.currency_code;
                """, (user_id, currency_code))
                logger.info(f"Main currency {currency_code} set for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting main currency {currency_code} for user {user_id}: {e}")
            raise

    async def remove_user_main_currency(self, user_id: int) -> None:
        """Remove main currency for a user."""
        logger.info(f"Removing main currency for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute("DELETE FROM main_currency WHERE user_id = ?", (user_id,))
                logger.info(f"Main currency removed for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing main currency for user {user_id}: {e}")
            raise

    async def get_unique_month_year_combinations(self, user_id: int) -> List[Tuple[str, str]]:
        """Get unique month-year combinations for a user's spendings."""
        logger.debug(f"Fetching unique month-year combinations for user {user_id}")
        query = """
            SELECT DISTINCT strftime('%m', date) as month, strftime('%Y', date) as year
            FROM spendings
            WHERE user_id = ?
            ORDER BY year DESC, month DESC
        """
        try:
            async with self.connection() as cursor:
                await cursor.execute(query, (user_id,))
                combinations = await cursor.fetchall()
                logger.debug(f"Retrieved {len(combinations)} month-year combinations for user {user_id}")
                return combinations
        except Exception as e:
            logger.error(f"Error fetching month-year combinations for user {user_id}: {e}")
            return []

    async def get_spending_data_for_month(
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
            async with self.connection() as cursor:
                await cursor.execute(query, (user_id, year, month))
                data = await cursor.fetchall()
                logger.debug(f"Retrieved {len(data)} spending records")
                return data
        except Exception as e:
            logger.error(f"Error fetching spending data: {e}")
            return []

    async def get_spending_totals_by_category(
        self, user_id: int, year: str, month: str
    ) -> List[Tuple[str, float, str]]:
        """Get spending totals grouped by category for a specific month."""
        logger.debug(f"Fetching spending totals by category for user {user_id} for {month}/{year}")
        try:
            async with self.connection() as cursor:
                await cursor.execute("""
                    SELECT category, SUM(amount) as total, currency
                    FROM spendings
                    WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
                    GROUP BY category, currency
                """, (user_id, year, month))
                totals = await cursor.fetchall()
                logger.debug(f"Retrieved {len(totals)} spending totals")
                return totals
        except Exception as e:
            logger.error(f"Error fetching spending totals: {e}")
            return []

    async def add_spending(
        self, user_id: int, description: str, amount: float,
        currency: str, category: str, spend_date: str
    ) -> None:
        """Add a new spending record."""
        logger.info(f"Adding spending for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute("""
                    INSERT INTO spendings (
                        user_id, description, amount, currency, category, date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, description, amount, currency, category, spend_date))
                logger.info(f"Spending added successfully")
        except Exception as e:
            logger.error(f"Error adding spending: {e}")
            raise

    async def remove_spending(self, user_id: int, spending_id: int) -> bool:
        """Remove a spending record."""
        logger.info(f"Removing spending with ID {spending_id} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
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

    async def export_all_spendings(
        self, user_id: int
    ) -> List[Tuple[str, float, str, str, str]]:
        """Export all spendings for a user."""
        logger.debug(f"Exporting all spendings for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute("""
                    SELECT description, amount, currency, category, date
                    FROM spendings
                    WHERE user_id = ?
                    ORDER BY date DESC, id DESC
                """, (user_id,))
                spendings = await cursor.fetchall()
                logger.debug(f"Exported {len(spendings)} spendings")
                return spendings
        except Exception as e:
            logger.error(f"Error exporting spendings: {e}")
            return []

    async def get_spendings_count(self, user_id: int) -> int:
        """Get total number of spendings for a user."""
        logger.debug(f"Fetching total spendings count for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM spendings WHERE user_id = ?",
                    (user_id,)
                )
                count = (await cursor.fetchone())[0]
                logger.debug(f"Total spendings count: {count}")
                return count
        except Exception as e:
            logger.error(f"Error fetching spendings count: {e}")
            return 0

    async def get_paginated_spendings(
        self, user_id: int, offset: int = 0, limit: int = 10
    ) -> List[Tuple[int, str, float, str, str, str]]:
        """Get paginated spendings for a user."""
        logger.debug(f"Fetching paginated spendings for user {user_id}, offset {offset}, limit {limit}")
        try:
            async with self.connection() as cursor:
                await cursor.execute("""
                    SELECT id, description, amount, currency, category, date
                    FROM spendings
                    WHERE user_id = ?
                    ORDER BY date DESC, id DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                spendings = await cursor.fetchall()
                logger.debug(f"Retrieved {len(spendings)} spendings")
                return spendings
        except Exception as e:
            logger.error(f"Error fetching paginated spendings: {e}")
            return []

    async def search_spendings(
        self, user_id: int, query: str = None, amount: float = None,
        offset: int = 0, limit: int = 10
    ) -> List[Tuple[int, str, float, str, str, str]]:
        """Search spendings by description or amount.

        Args:
            user_id: The user ID
            query: Text to search in description
            amount: Exact amount to search for
            offset: Pagination offset
            limit: Number of items per page

        Returns:
            List of tuples containing (id, description, amount, currency, category, date)
        """
        logger.debug(f"Searching spendings for user {user_id}")
        try:
            async with self.connection() as cursor:
                params = [user_id]
                sql = """
                    SELECT id, description, amount, currency, category, date
                    FROM spendings
                    WHERE user_id = ?
                """

                if query:
                    sql += " AND LOWER(description) LIKE LOWER(?)"
                    params.append(f"%{query}%")

                if amount is not None:
                    sql += " AND amount = ?"
                    params.append(amount)

                sql += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                await cursor.execute(sql, params)
                results = await cursor.fetchall()
                logger.debug(f"Found {len(results)} matching spendings")
                return results
        except Exception as e:
            logger.error(f"Error searching spendings: {e}")
            return []

    async def count_search_results(
        self, user_id: int, query: str = None, amount: float = None
    ) -> int:
        """Count total number of search results.

        Args:
            user_id: The user ID
            query: Text to search in description
            amount: Exact amount to search for

        Returns:
            Total number of matching spendings
        """
        logger.debug(f"Counting search results for user {user_id}")
        try:
            async with self.connection() as cursor:
                params = [user_id]
                sql = "SELECT COUNT(*) FROM spendings WHERE user_id = ?"

                if query:
                    sql += " AND LOWER(description) LIKE LOWER(?)"
                    params.append(f"%{query}%")

                if amount is not None:
                    sql += " AND amount = ?"
                    params.append(amount)

                await cursor.execute(sql, params)
                count = (await cursor.fetchone())[0]
                logger.debug(f"Found {count} total matching spendings")
                return count
        except Exception as e:
            logger.error(f"Error counting search results: {e}")
            return 0

    async def get_spending_by_id(
        self, user_id: int, spending_id: int
    ) -> Optional[Spending]:
        """Get details of a specific spending record."""
        logger.debug(f"Fetching details for spending ID {spending_id} for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT * FROM spendings WHERE id = ? AND user_id = ?",
                    (spending_id, user_id)
                )
                row = await cursor.fetchone()
                if row:
                    # Convert the aiosqlite.Row to a tuple
                    row_tuple = tuple(row)
                    spending = Spending.from_row(row_tuple)
                    logger.debug(f"Retrieved spending details: {spending}")
                    return spending
                else:
                    logger.warning(f"Spending ID {spending_id} not found for user {user_id}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching spending details: {e}")
            return None


# Create global database instance
db = Database()
