"""
Alembic environment configuration for DBStudio.

This module is executed by Alembic for every migration command. It imports
the application's SQLAlchemy models so that Alembic can autogenerate
migration scripts by comparing the model definitions against the live
database schema.

Usage:
    # From the backend/ directory:
    alembic revision --autogenerate -m "describe change"
    alembic upgrade head
    alembic downgrade -1
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import application models so Alembic can detect schema changes
from app.database.models import Base  # noqa: F401
from app.config import settings

# Alembic Config object -- provides access to alembic.ini values.
config = context.config

# Interpret the config file for Python logging if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate support.
target_metadata = Base.metadata

# Override the sqlalchemy.url from application settings if available.
# Convert async URL to sync URL for Alembic (Alembic does not support
# async drivers natively in all operations).
_db_url = settings.DATABASE_URL
# Convert async driver prefixes to sync equivalents
_db_url = _db_url.replace("sqlite+aiosqlite://", "sqlite://")
_db_url = _db_url.replace("postgresql+asyncpg://", "postgresql://")
_db_url = _db_url.replace("mysql+aiomysql://", "mysql+pymysql://")
config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine. Calls to
    context.execute() emit the SQL string to the script output rather
    than executing against the database.
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


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against an active connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations.

    This is necessary because the application uses an async SQLAlchemy
    driver (aiosqlite). We create a temporary async engine, obtain a
    connection, and run migrations synchronously within that connection.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
