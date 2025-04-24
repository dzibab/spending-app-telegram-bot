import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiosqlite

from constants import DEFAULT_CATEGORIES, DEFAULT_CURRENCIES
from utils.logging import logger


@dataclass
class Spending:
    """Represents a spending record."""

    id: int | None
    user_id: int
    description: str
    amount: float
    currency: str
    category: str
    date: str

    @classmethod
    def from_row(cls, row: tuple) -> "Spending":
        """Create a Spending instance from a database row."""
        return cls(
            id=row[0],
            user_id=row[1],
            description=row[2],
            amount=row[3],
            currency=row[4],
            category=row[5],
            date=row[6],
        )


class Cache:
    """Cache implementation for frequently accessed database data."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with time-to-live in seconds."""
        self._data: dict[str, dict[Any, tuple[Any, datetime]]] = {}
        self._ttl = ttl_seconds

    def get(self, cache_type: str, key: Any) -> Any | None:
        """Get a value from cache if it exists and is not expired."""
        if cache_type not in self._data or key not in self._data[cache_type]:
            return None

        value, timestamp = self._data[cache_type][key]
        if datetime.now() > timestamp:
            # Cache entry has expired
            del self._data[cache_type][key]
            return None

        return value

    def set(self, cache_type: str, key: Any, value: Any) -> None:
        """Store a value in cache with expiration time."""
        if cache_type not in self._data:
            self._data[cache_type] = {}

        expiry = datetime.now() + timedelta(seconds=self._ttl)
        self._data[cache_type][key] = (value, expiry)

    def invalidate(self, cache_type: str, key: Any | None = None) -> None:
        """Invalidate a specific cache entry or all entries of a given type."""
        if cache_type not in self._data:
            return

        if key is not None:
            if key in self._data[cache_type]:
                del self._data[cache_type][key]
        else:
            self._data[cache_type] = {}


class Database:
    """Handles database operations for the spending tracker bot."""

    def __init__(self, db_path: str = "spendings.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._connection = None
        self._connection_lock = asyncio.Lock()
        self._connection_pool = []  # Simple connection pool
        self._pool_size = 3  # Maximum number of connections in the pool
        self._pool_lock = asyncio.Lock()

        # Initialize different caches with appropriate TTLs
        # Static data like categories/currencies can be cached longer
        self._user_settings_cache = Cache(ttl_seconds=1800)  # 30 minutes for user settings
        self._search_cache = Cache(ttl_seconds=60)  # 1 minute for search results
        self._reports_cache = Cache(ttl_seconds=3600)  # 1 hour for historical reports
        self._dynamic_data_cache = Cache(ttl_seconds=300)  # 5 minutes for other data

        # Cache types
        self.CACHE_USER_CURRENCIES = "user_currencies"
        self.CACHE_USER_CATEGORIES = "user_categories"
        self.CACHE_USER_MAIN_CURRENCY = "user_main_currency"
        self.CACHE_SPENDING_COUNT = "spending_count"
        self.CACHE_SEARCH_RESULTS = "search_results"
        self.CACHE_SEARCH_COUNT = "search_count"
        self.CACHE_REPORT_DATA = "monthly_report"
        self.CACHE_FREQUENTLY_USED = "frequently_used"

    async def get_connection(self) -> aiosqlite.Connection:
        """Get a database connection from the pool or create a new one."""
        async with self._pool_lock:
            # Try to get a connection from the pool
            if self._connection_pool:
                connection = self._connection_pool.pop()
                logger.debug("Reusing connection from pool")
                return connection

        # No connection in the pool, create a new one
        logger.debug("Opening new async database connection")
        connection = await aiosqlite.connect(self.db_path)
        # Enable foreign keys
        await connection.execute("PRAGMA foreign_keys = ON")
        # Optimize SQLite for performance
        await connection.execute("PRAGMA journal_mode = WAL")
        await connection.execute("PRAGMA synchronous = NORMAL")
        await connection.execute("PRAGMA temp_store = MEMORY")
        await connection.execute("PRAGMA mmap_size = 30000000000")
        await connection.execute("PRAGMA cache_size = -32000")  # 32MB cache (-ve number means KB)

        # Make aiosqlite return rows as Row objects accessible by column name
        connection.row_factory = aiosqlite.Row
        return connection

    async def release_connection(self, connection: aiosqlite.Connection) -> None:
        """Release connection back to the pool or close it."""
        async with self._pool_lock:
            # If pool is not full, return connection to pool
            if len(self._connection_pool) < self._pool_size:
                self._connection_pool.append(connection)
                logger.debug("Connection released back to pool")
                return

        # If pool is full, just close the connection
        await connection.close()
        logger.debug("Connection pool full, closed connection")

    async def close(self) -> None:
        """Close all database connections in the pool."""
        logger.info("Closing all database connections")
        async with self._pool_lock:
            for connection in self._connection_pool:
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"Error closing pooled connection: {e}")
            self._connection_pool.clear()

        # Close primary connection if exists
        async with self._connection_lock:
            if self._connection:
                await self._connection.close()
                self._connection = None
                logger.debug("Closed primary database connection")

        logger.info("All database connections closed")

    @asynccontextmanager
    async def connection(self):
        """Async context manager for database connections."""
        conn = await self.get_connection()
        try:
            async with conn.cursor() as cursor:
                yield cursor
        finally:
            # Return connection to the pool
            await self.release_connection(conn)

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
        finally:
            # Return connection to the pool
            await self.release_connection(conn)

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
                # Create indexes to optimize common queries
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_user_date ON spendings(user_id, date);"
                )
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_user_category ON spendings(user_id, category);"
                )
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_user_currency ON spendings(user_id, currency);"
                )
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_amount ON spendings(amount);"
                )
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_description ON spendings(description COLLATE NOCASE);"
                )
                # Add a compound index to improve search queries that filter by both user_id and description
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_user_desc ON spendings(user_id, description COLLATE NOCASE);"
                )
                # Add compound index for sorting patterns (common in pagination)
                await cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_spendings_user_date_id ON spendings(user_id, date DESC, id DESC);"
                )

                # Create currencies table with composite primary key
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS currencies (
                        user_id INTEGER NOT NULL,
                        currency_code TEXT NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        PRIMARY KEY (user_id, currency_code)
                    );
                """)

                # Create categories table with composite primary key
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        user_id INTEGER NOT NULL,
                        category_name TEXT NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
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

    async def migrate_database(self) -> None:
        """Migrate database to add new columns if needed."""
        logger.info("Checking if database migration is needed")
        try:
            async with self.connection() as cursor:
                # Check if is_active column exists in currencies table
                await cursor.execute("PRAGMA table_info(currencies)")
                currencies_columns = await cursor.fetchall()
                has_is_active_currencies = any(col[1] == "is_active" for col in currencies_columns)

                # Check if is_active column exists in categories table
                await cursor.execute("PRAGMA table_info(categories)")
                categories_columns = await cursor.fetchall()
                has_is_active_categories = any(col[1] == "is_active" for col in categories_columns)

                # Add is_active column to currencies if needed
                if not has_is_active_currencies:
                    logger.info("Adding is_active column to currencies table")
                    await cursor.execute(
                        "ALTER TABLE currencies ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                    )

                # Add is_active column to categories if needed
                if not has_is_active_categories:
                    logger.info("Adding is_active column to categories table")
                    await cursor.execute(
                        "ALTER TABLE categories ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                    )

                if not has_is_active_currencies or not has_is_active_categories:
                    logger.info("Database migration completed successfully")
                else:
                    logger.info("No database migration needed")
        except Exception as e:
            logger.error(f"Error migrating database: {e}")
            raise

    async def initialize_user_currencies(self, user_id: int) -> None:
        """Initialize default currencies for a user."""
        logger.info(f"Initializing default currencies for user {user_id}")
        try:
            async with self.transaction() as cursor:
                # Check if user already has currencies
                await cursor.execute(
                    "SELECT 1 FROM currencies WHERE user_id = ? LIMIT 1;", (user_id,)
                )
                currencies_exist = await cursor.fetchone()

                if currencies_exist:
                    logger.debug(f"User {user_id} already has currencies initialized")
                    return

                # Initialize default currencies
                default_currencies = [(user_id, currency) for currency in DEFAULT_CURRENCIES]
                await cursor.executemany(
                    "INSERT INTO currencies (user_id, currency_code) VALUES (?, ?);",
                    default_currencies,
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
                    "SELECT 1 FROM categories WHERE user_id = ? LIMIT 1;", (user_id,)
                )
                categories_exist = await cursor.fetchone()

                if categories_exist:
                    logger.debug(f"User {user_id} already has categories initialized")
                    return

                # Initialize default categories
                default_categories = [(user_id, category) for category in DEFAULT_CATEGORIES]
                await cursor.executemany(
                    "INSERT INTO categories (user_id, category_name) VALUES (?, ?);",
                    default_categories,
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

    async def get_user_currencies(self, user_id: int, include_archived: bool = False) -> list[str]:
        """Get list of currencies for a user.

        Args:
            user_id: The user ID
            include_archived: Whether to include archived currencies in the result

        Returns:
            List of currency codes
        """
        logger.debug(f"Fetching currencies for user {user_id}, include_archived={include_archived}")
        try:
            # Check cache first - only use cache for active currencies
            if not include_archived:
                cached_currencies = self._user_settings_cache.get(
                    self.CACHE_USER_CURRENCIES, user_id
                )
                if cached_currencies is not None:
                    logger.debug(f"Cache hit for user {user_id} currencies")
                    return cached_currencies

            async with self.connection() as cursor:
                query = "SELECT currency_code FROM currencies WHERE user_id = ?"
                if not include_archived:
                    query += " AND is_active = 1"

                await cursor.execute(query, (user_id,))
                rows = await cursor.fetchall()
                currencies = [row[0] for row in rows]
                logger.debug(f"Retrieved {len(currencies)} currencies for user {user_id}")

                # Update cache only for active currencies
                if not include_archived:
                    self._user_settings_cache.set(self.CACHE_USER_CURRENCIES, user_id, currencies)
                return currencies
        except Exception as e:
            logger.error(f"Error fetching currencies for user {user_id}: {e}")
            return []

    async def get_user_categories(self, user_id: int, include_archived: bool = False) -> list[str]:
        """Get list of categories for a user.

        Args:
            user_id: The user ID
            include_archived: Whether to include archived categories in the result

        Returns:
            List of category names
        """
        logger.debug(f"Fetching categories for user {user_id}, include_archived={include_archived}")
        try:
            # Check cache first - only use cache for active categories
            if not include_archived:
                cached_categories = self._user_settings_cache.get(
                    self.CACHE_USER_CATEGORIES, user_id
                )
                if cached_categories is not None:
                    logger.debug(f"Cache hit for user {user_id} categories")
                    return cached_categories

            async with self.connection() as cursor:
                query = "SELECT category_name FROM categories WHERE user_id = ?"
                if not include_archived:
                    query += " AND is_active = 1"

                await cursor.execute(query, (user_id,))
                rows = await cursor.fetchall()
                categories = [row[0] for row in rows]
                logger.debug(f"Retrieved {len(categories)} categories for user {user_id}")

                # Update cache only for active categories
                if not include_archived:
                    self._user_settings_cache.set(self.CACHE_USER_CATEGORIES, user_id, categories)
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
                    (user_id, currency),
                )
                logger.info(f"Currency {currency} added for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CURRENCIES, user_id)
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
                    (user_id, category),
                )
                logger.info(f"Category {category} added for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CATEGORIES, user_id)
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
                    (user_id, currency),
                )
                # In aiosqlite, rowcount is available after execution
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Currency {currency} removed for user {user_id}")
                else:
                    logger.warning(f"Currency {currency} not found for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CURRENCIES, user_id)
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
                    (user_id, category),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Category {category} removed for user {user_id}")
                else:
                    logger.warning(f"Category {category} not found for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CATEGORIES, user_id)
                return success
        except Exception as e:
            logger.error(f"Error removing category {category} for user {user_id}: {e}")
            return False

    async def archive_currency(self, user_id: int, currency: str) -> bool:
        """Archive (hide) a currency instead of deleting it.

        Args:
            user_id: The user ID
            currency: Currency code to archive

        Returns:
            Whether the operation was successful
        """
        logger.info(f"Archiving currency {currency} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "UPDATE currencies SET is_active = 0 WHERE user_id = ? AND currency_code = ?;",
                    (user_id, currency),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Currency {currency} archived for user {user_id}")
                else:
                    logger.warning(f"Currency {currency} not found for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CURRENCIES, user_id)
                return success
        except Exception as e:
            logger.error(f"Error archiving currency {currency} for user {user_id}: {e}")
            return False

    async def unarchive_currency(self, user_id: int, currency: str) -> bool:
        """Unarchive (unhide) a previously archived currency.

        Args:
            user_id: The user ID
            currency: Currency code to unarchive

        Returns:
            Whether the operation was successful
        """
        logger.info(f"Unarchiving currency {currency} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "UPDATE currencies SET is_active = 1 WHERE user_id = ? AND currency_code = ?;",
                    (user_id, currency),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Currency {currency} unarchived for user {user_id}")
                else:
                    logger.warning(f"Currency {currency} not found for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CURRENCIES, user_id)
                return success
        except Exception as e:
            logger.error(f"Error unarchiving currency {currency} for user {user_id}: {e}")
            return False

    async def archive_category(self, user_id: int, category: str) -> bool:
        """Archive (hide) a category instead of deleting it.

        Args:
            user_id: The user ID
            category: Category name to archive

        Returns:
            Whether the operation was successful
        """
        logger.info(f"Archiving category {category} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "UPDATE categories SET is_active = 0 WHERE user_id = ? AND category_name = ?;",
                    (user_id, category),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Category {category} archived for user {user_id}")
                else:
                    logger.warning(f"Category {category} not found for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CATEGORIES, user_id)
                return success
        except Exception as e:
            logger.error(f"Error archiving category {category} for user {user_id}: {e}")
            return False

    async def unarchive_category(self, user_id: int, category: str) -> bool:
        """Unarchive (unhide) a previously archived category.

        Args:
            user_id: The user ID
            category: Category name to unarchive

        Returns:
            Whether the operation was successful
        """
        logger.info(f"Unarchiving category {category} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "UPDATE categories SET is_active = 1 WHERE user_id = ? AND category_name = ?;",
                    (user_id, category),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Category {category} unarchived for user {user_id}")
                else:
                    logger.warning(f"Category {category} not found for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_CATEGORIES, user_id)
                return success
        except Exception as e:
            logger.error(f"Error unarchiving category {category} for user {user_id}: {e}")
            return False

    async def get_archived_currencies(self, user_id: int) -> list[str]:
        """Get list of archived currencies for a user.

        Args:
            user_id: The user ID

        Returns:
            List of archived currency codes
        """
        logger.debug(f"Fetching archived currencies for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT currency_code FROM currencies WHERE user_id = ? AND is_active = 0",
                    (user_id,),
                )
                rows = await cursor.fetchall()
                archived_currencies = [row[0] for row in rows]
                logger.debug(f"Retrieved {len(archived_currencies)} archived currencies")
                return archived_currencies
        except Exception as e:
            logger.error(f"Error fetching archived currencies for user {user_id}: {e}")
            return []

    async def get_archived_categories(self, user_id: int) -> list[str]:
        """Get list of archived categories for a user.

        Args:
            user_id: The user ID

        Returns:
            List of archived category names
        """
        logger.debug(f"Fetching archived categories for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT category_name FROM categories WHERE user_id = ? AND is_active = 0",
                    (user_id,),
                )
                rows = await cursor.fetchall()
                archived_categories = [row[0] for row in rows]
                logger.debug(f"Retrieved {len(archived_categories)} archived categories")
                return archived_categories
        except Exception as e:
            logger.error(f"Error fetching archived categories for user {user_id}: {e}")
            return []

    async def get_user_main_currency(self, user_id: int) -> str | None:
        """Get main currency for a user."""
        logger.debug(f"Fetching main currency for user {user_id}")
        try:
            # Check cache first
            cached_main_currency = self._user_settings_cache.get(
                self.CACHE_USER_MAIN_CURRENCY, user_id
            )
            if cached_main_currency is not None:
                logger.debug(f"Cache hit for user {user_id} main currency")
                return cached_main_currency

            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT currency_code FROM main_currency WHERE user_id = ?", (user_id,)
                )
                row = await cursor.fetchone()
                main_currency = row[0] if row else None
                logger.debug(f"Main currency for user {user_id}: {main_currency}")

                # Update cache
                self._user_settings_cache.set(self.CACHE_USER_MAIN_CURRENCY, user_id, main_currency)
                return main_currency
        except Exception as e:
            logger.error(f"Error fetching main currency for user {user_id}: {e}")
            return None

    async def set_user_main_currency(self, user_id: int, currency_code: str) -> None:
        """Set main currency for a user."""
        logger.info(f"Setting main currency {currency_code} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO main_currency (user_id, currency_code)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET currency_code = excluded.currency_code;
                """,
                    (user_id, currency_code),
                )
                logger.info(f"Main currency {currency_code} set for user {user_id}")

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_MAIN_CURRENCY, user_id)
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

                # Invalidate cache
                self._user_settings_cache.invalidate(self.CACHE_USER_MAIN_CURRENCY, user_id)
        except Exception as e:
            logger.error(f"Error removing main currency for user {user_id}: {e}")
            raise

    async def get_unique_month_year_combinations(self, user_id: int) -> list[tuple[str, str]]:
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
                logger.debug(
                    f"Retrieved {len(combinations)} month-year combinations for user {user_id}"
                )
                return combinations
        except Exception as e:
            logger.error(f"Error fetching month-year combinations for user {user_id}: {e}")
            return []

    async def get_spending_data_for_month(
        self, user_id: int, year: str, month: str
    ) -> list[tuple[str, float, str]]:
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
    ) -> list[tuple[str, float, str]]:
        """Get spending totals grouped by category for a specific month."""
        logger.debug(f"Fetching spending totals by category for user {user_id} for {month}/{year}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    """
                    SELECT category, SUM(amount) as total, currency
                    FROM spendings
                    WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
                    GROUP BY category, currency
                """,
                    (user_id, year, month),
                )
                totals = await cursor.fetchall()
                logger.debug(f"Retrieved {len(totals)} spending totals")
                return totals
        except Exception as e:
            logger.error(f"Error fetching spending totals: {e}")
            return []

    async def add_spending(
        self,
        user_id: int,
        description: str,
        amount: float,
        currency: str,
        category: str,
        spend_date: str,
    ) -> None:
        """Add a new spending record."""
        logger.info(f"Adding spending for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO spendings (
                        user_id, description, amount, currency, category, date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (user_id, description, amount, currency, category, spend_date),
                )
                logger.info("Spending added successfully")

                # Invalidate spending count cache
                self._dynamic_data_cache.invalidate(self.CACHE_SPENDING_COUNT, user_id)
        except Exception as e:
            logger.error(f"Error adding spending: {e}")
            raise

    async def bulk_add_spendings(
        self, spendings: list[tuple[int, str, float, str, str, str]]
    ) -> int:
        """Add multiple spending records in a single transaction for better performance.

        Args:
            spendings: List of tuples containing (user_id, description, amount, currency, category, date)

        Returns:
            Number of records successfully added
        """
        logger.info(f"Bulk adding {len(spendings)} spending records")
        try:
            async with self.transaction() as cursor:
                await cursor.executemany(
                    """
                    INSERT INTO spendings (
                        user_id, description, amount, currency, category, date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    spendings,
                )
                logger.info(f"Successfully added {len(spendings)} spending records")

                # Get unique user IDs to invalidate cache
                user_ids = {spending[0] for spending in spendings}
                for user_id in user_ids:
                    self._dynamic_data_cache.invalidate(self.CACHE_SPENDING_COUNT, user_id)

                return len(spendings)
        except Exception as e:
            logger.error(f"Error bulk adding spendings: {e}")
            return 0

    async def remove_spending(self, user_id: int, spending_id: int) -> bool:
        """Remove a spending record."""
        logger.info(f"Removing spending with ID {spending_id} for user {user_id}")
        try:
            async with self.transaction() as cursor:
                await cursor.execute(
                    "DELETE FROM spendings WHERE id = ? AND user_id = ?", (spending_id, user_id)
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info("Spending removed successfully")

                    # Invalidate spending count cache
                    self._dynamic_data_cache.invalidate(self.CACHE_SPENDING_COUNT, user_id)
                else:
                    logger.warning("Spending not found")
                return success
        except Exception as e:
            logger.error(f"Error removing spending: {e}")
            return False

    async def export_all_spendings(self, user_id: int) -> list[Spending]:
        """Export all spendings for a user."""
        logger.debug(f"Exporting all spendings for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    """
                    SELECT *
                    FROM spendings
                    WHERE user_id = ?
                    ORDER BY date DESC, id DESC
                """,
                    (user_id,),
                )
                rows = await cursor.fetchall()
                spendings = [Spending.from_row(tuple(row)) for row in rows]
                logger.debug(f"Exported {len(spendings)} spendings")
                return spendings
        except Exception as e:
            logger.error(f"Error exporting spendings: {e}")
            return []

    async def export_spendings_with_date_range(
        self, user_id: int, start_date: datetime = None, end_date: datetime = None
    ) -> list[Spending]:
        """Export spendings for a user within a specific date range.

        Args:
            user_id: The user ID
            start_date: Optional start date for filtering (inclusive)
            end_date: Optional end date for filtering (inclusive)

        Returns:
            List of Spending objects within the date range
        """
        logger.debug(f"Exporting spendings for user {user_id} with date range filter")
        try:
            async with self.connection() as cursor:
                params = [user_id]
                sql = """
                    SELECT *
                    FROM spendings
                    WHERE user_id = ?
                """

                # Add date range filters if provided
                if start_date:
                    sql += " AND date(date) >= date(?)"
                    params.append(start_date.strftime("%Y-%m-%d"))

                if end_date:
                    sql += " AND date(date) <= date(?)"
                    params.append(end_date.strftime("%Y-%m-%d"))

                # Use chunked processing for large datasets
                sql += " ORDER BY date DESC, id DESC"

                # For very large datasets, we'll process in chunks
                chunk_size = 1000
                sql_with_limit = f"{sql} LIMIT ? OFFSET ?"

                all_spendings = []
                offset = 0

                while True:
                    query_params = params.copy()
                    query_params.extend([chunk_size, offset])
                    await cursor.execute(sql_with_limit, query_params)
                    rows = await cursor.fetchall()
                    if not rows:
                        break

                    spendings = [Spending.from_row(tuple(row)) for row in rows]
                    all_spendings.extend(spendings)

                    if len(rows) < chunk_size:
                        break

                    offset += chunk_size

                logger.debug(f"Exported {len(all_spendings)} spendings within date range")
                return all_spendings
        except Exception as e:
            logger.error(f"Error exporting spendings with date range: {e}")
            return []

    async def get_spendings_count(self, user_id: int) -> int:
        """Get total number of spendings for a user."""
        logger.debug(f"Fetching total spendings count for user {user_id}")
        try:
            # Check cache first
            cached_count = self._dynamic_data_cache.get(self.CACHE_SPENDING_COUNT, user_id)
            if cached_count is not None:
                logger.debug(f"Cache hit for user {user_id} spending count")
                return cached_count

            async with self.connection() as cursor:
                await cursor.execute("SELECT COUNT(*) FROM spendings WHERE user_id = ?", (user_id,))
                count = (await cursor.fetchone())[0]
                logger.debug(f"Total spendings count: {count}")

                # Update cache
                self._dynamic_data_cache.set(self.CACHE_SPENDING_COUNT, user_id, count)
                return count
        except Exception as e:
            logger.error(f"Error fetching spendings count: {e}")
            return 0

    async def get_paginated_spendings(
        self, user_id: int, offset: int = 0, limit: int = 10
    ) -> list[Spending]:
        """Get paginated spendings for a user."""
        logger.debug(
            f"Fetching paginated spendings for user {user_id}, offset {offset}, limit {limit}"
        )
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    """
                    SELECT *
                    FROM spendings
                    WHERE user_id = ?
                    ORDER BY date DESC, id DESC
                    LIMIT ? OFFSET ?
                """,
                    (user_id, limit, offset),
                )
                rows = await cursor.fetchall()
                spendings = [Spending.from_row(tuple(row)) for row in rows]
                logger.debug(f"Retrieved {len(spendings)} spendings")
                return spendings
        except Exception as e:
            logger.error(f"Error fetching paginated spendings: {e}")
            return []

    async def search_spendings(
        self,
        user_id: int,
        query: str = None,
        amount: float = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[Spending]:
        """Search spendings by description or amount.

        Args:
            user_id: The user ID
            query: Text to search in description
            amount: Exact amount to search for
            offset: Pagination offset
            limit: Number of items per page

        Returns:
            List of Spending objects matching the search criteria
        """
        logger.debug(f"Searching spendings for user {user_id}")
        try:
            # Create a cache key based on search params
            cache_key = f"search:{user_id}:{query}:{amount}:{offset}:{limit}"
            cache_type = self.CACHE_SEARCH_RESULTS

            # Check cache first for frequent identical searches
            cached_results = self._search_cache.get(cache_type, cache_key)
            if cached_results is not None:
                logger.debug(f"Cache hit for search results with key {cache_key}")
                return cached_results

            async with self.connection() as cursor:
                params = [user_id]
                sql = """
                    SELECT *
                    FROM spendings
                    WHERE user_id = ?
                """

                if query:
                    # Use user_desc index for better performance
                    sql += " AND LOWER(description) LIKE LOWER(?)"
                    params.append(f"%{query}%")

                if amount is not None:
                    sql += " AND amount = ?"
                    params.append(amount)

                sql += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                await cursor.execute(sql, params)
                rows = await cursor.fetchall()
                spendings = [Spending.from_row(tuple(row)) for row in rows]
                logger.debug(f"Found {len(spendings)} matching spendings")

                # Cache results
                self._search_cache.set(cache_type, cache_key, spendings)
                return spendings
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
            # Create a cache key based on search params
            cache_key = f"count:{user_id}:{query}:{amount}"
            cache_type = self.CACHE_SEARCH_COUNT

            # Check cache first for frequent identical searches
            cached_count = self._search_cache.get(cache_type, cache_key)
            if cached_count is not None:
                logger.debug(f"Cache hit for search count with key {cache_key}")
                return cached_count

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

                # Cache the count result
                self._search_cache.set(cache_type, cache_key, count)
                return count
        except Exception as e:
            logger.error(f"Error counting search results: {e}")
            return 0

    async def get_spending_by_id(self, user_id: int, spending_id: int) -> Spending | None:
        """Get details of a specific spending record."""
        logger.debug(f"Fetching details for spending ID {spending_id} for user {user_id}")
        try:
            async with self.connection() as cursor:
                await cursor.execute(
                    "SELECT * FROM spendings WHERE id = ? AND user_id = ?", (spending_id, user_id)
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

    async def get_monthly_report_data(self, user_id: int, year: str, month: str) -> dict:
        """Get optimized spending data for monthly reports in a single query.

        This combines multiple data needs for report generation into a single
        optimized query to reduce database hits and improve performance.

        Args:
            user_id: The user ID
            year: Year in string format (YYYY)
            month: Month in string format (MM)

        Returns:
            Dictionary with spending data grouped by category and totals
        """
        logger.debug(
            f"Fetching optimized monthly report data for user {user_id} for {month}/{year}"
        )

        # Get current year and month for comparison
        current_date = datetime.now()
        current_year = str(current_date.year)
        current_month = f"{current_date.month:02d}"

        # Only use cache for months other than the current month
        is_current_month = year == current_year and month == current_month

        if not is_current_month:
            # Create a cache key for this specific report
            cache_key = f"{user_id}:{year}:{month}"
            cache_type = self.CACHE_REPORT_DATA

            # Check if we have cached results for this report
            cached_data = self._reports_cache.get(cache_type, cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for monthly report data with key {cache_key}")
                return cached_data
        else:
            logger.debug(f"Skipping cache for current month ({month}/{year})")

        try:
            # We'll use a more comprehensive query to get all needed data at once
            query = """
                SELECT
                    category,
                    SUM(amount) as total,
                    currency,
                    COUNT(*) as count
                FROM spendings
                WHERE user_id = ?
                AND strftime('%Y', date) = ?
                AND strftime('%m', date) = ?
                GROUP BY category, currency
                ORDER BY total DESC
            """

            async with self.connection() as cursor:
                await cursor.execute(query, (user_id, year, month))
                rows = await cursor.fetchall()

                # Process the data into a structure that's easy to work with
                result = {
                    "by_category": {},
                    "by_currency": {},
                    "total_transactions": 0,
                    "total_amount": 0.0,
                    "categories": set(),
                    "currencies": set(),
                }

                # Process each row of data
                for row in rows:
                    category = row[0]
                    amount = row[1]
                    currency = row[2]
                    count = row[3]

                    # Add to categories set
                    result["categories"].add(category)
                    result["currencies"].add(currency)

                    # Track total transactions
                    result["total_transactions"] += count

                    # Group by category
                    if category not in result["by_category"]:
                        result["by_category"][category] = []
                    result["by_category"][category].append(
                        {"amount": amount, "currency": currency, "count": count}
                    )

                    # Group by currency
                    if currency not in result["by_currency"]:
                        result["by_currency"][currency] = {"total": 0.0, "categories": {}}

                    if category not in result["by_currency"][currency]["categories"]:
                        result["by_currency"][currency]["categories"][category] = 0.0

                    result["by_currency"][currency]["categories"][category] += amount
                    result["by_currency"][currency]["total"] += amount

                # Convert sets to lists for easier serialization
                result["categories"] = list(result["categories"])
                result["currencies"] = list(result["currencies"])

                # Only cache if not the current month
                if not is_current_month:
                    self._reports_cache.set(self.CACHE_REPORT_DATA, cache_key, result)
                    logger.debug(f"Cached monthly report data with key {cache_key}")

                logger.debug(f"Retrieved comprehensive report data with {len(rows)} records")
                return result
        except Exception as e:
            logger.error(f"Error fetching monthly report data: {e}")
            return {
                "by_category": {},
                "by_currency": {},
                "total_transactions": 0,
                "categories": [],
                "currencies": [],
            }

    async def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a query and return the results.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of result rows
        """
        try:
            async with self.connection() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []

    async def get_frequently_used_categories(self, user_id: int, limit: int = 5) -> list[str]:
        """Get the most frequently used categories for a user.

        Args:
            user_id: The user ID to get categories for
            limit: Maximum number of categories to return

        Returns:
            List of category names ordered by frequency of use
        """
        query = """
            SELECT category, COUNT(*) as count
            FROM spendings
            WHERE user_id = ?
            GROUP BY category
            ORDER BY count DESC
            LIMIT ?
        """

        result = await self.execute_query(query, (user_id, limit))
        return [row[0] for row in result]

    async def get_recent_spendings_by_category(
        self, user_id: int, category: str, limit: int = 3
    ) -> list[dict]:
        """Get recent spending descriptions for a specific category.

        Args:
            user_id: The user ID to get spendings for
            category: The category to filter by
            limit: Maximum number of spendings to return

        Returns:
            List of spending dictionaries with description, amount and currency
        """
        query = """
            SELECT description, amount, currency
            FROM spendings
            WHERE user_id = ? AND category = ?
            ORDER BY date DESC
            LIMIT ?
        """

        result = await self.execute_query(query, (user_id, category, limit))
        return [{"description": row[0], "amount": row[1], "currency": row[2]} for row in result]


# Create global database instance
db = Database()
