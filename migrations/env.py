from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Create a MetaData instance
metadata = MetaData()

# Define Base for declarative class definitions
Base = declarative_base(metadata=metadata)


# Define your models here - these should match your existing database structure
class Spending(Base):
    __tablename__ = "spendings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    description = Column(String)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    category = Column(String, nullable=False)
    date = Column(String, nullable=False)


class Currency(Base):
    __tablename__ = "currencies"

    user_id = Column(Integer, primary_key=True)
    currency_code = Column(String, primary_key=True)
    is_active = Column(Boolean, nullable=False, default=True)


class Category(Base):
    __tablename__ = "categories"

    user_id = Column(Integer, primary_key=True)
    category_name = Column(String, primary_key=True)
    is_active = Column(Boolean, nullable=False, default=True)


class MainCurrency(Base):
    __tablename__ = "main_currency"

    user_id = Column(Integer, primary_key=True)
    currency_code = Column(String, nullable=False)


# Set target_metadata to the metadata from the Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite-friendly migrations
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
