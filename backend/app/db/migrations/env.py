"""
Alembic migration environment for the M1M backend.

Uses the asyncpg PostgreSQL driver and loads DATABASE_URL from .env.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

# env.py is located at:
# backend/app/db/migrations/env.py
#
# .env is located at:
# backend/.env
#
# Therefore we go up 3 directories:
# migrations -> db -> app -> backend

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..")
)

ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)


# ============================================================
# 2. ADD BACKEND TO PYTHON PATH
# ============================================================

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# 3. IMPORT DATABASE BASE AND MODELS
# ============================================================

from app.db.session import Base  # noqa: E402

# Import models so SQLAlchemy knows about all tables.
import app.models  # noqa: F401, E402


# ============================================================
# 4. ALEMBIC CONFIGURATION
# ============================================================

config = context.config


# Load Alembic logging configuration.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# SQLAlchemy metadata used for autogenerate.
target_metadata = Base.metadata


# ============================================================
# 5. GET DATABASE URL
# ============================================================

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Make sure backend/.env contains DATABASE_URL."
    )


# IMPORTANT:
# Alembic's ConfigParser treats '%' specially.
# Passwords containing %40, %21, etc. can therefore cause:
#
# ValueError: invalid interpolation syntax
#
# Escape '%' before putting the URL into Alembic config.

alembic_database_url = database_url.replace("%", "%%")

config.set_main_option(
    "sqlalchemy.url",
    alembic_database_url,
)


# ============================================================
# 6. OFFLINE MIGRATIONS
# ============================================================

def run_migrations_offline() -> None:
    """
    Run migrations without creating a database connection.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# 7. RUN MIGRATIONS WITH DATABASE CONNECTION
# ============================================================

def do_run_migrations(connection: Connection) -> None:
    """
    Configure Alembic and run migrations using
    an already-created database connection.
    """

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create an async SQLAlchemy engine using asyncpg
    and run the Alembic migrations.
    """

    # Use the DATABASE_URL directly rather than relying on
    # Alembic's ConfigParser.
    #
    # This guarantees that:
    # postgresql+asyncpg://
    #
    # is actually used.

    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:

        await connection.run_sync(
            do_run_migrations
        )

    await connectable.dispose()


# ============================================================
# 8. ONLINE MIGRATIONS
# ============================================================

def run_migrations_online() -> None:
    """
    Run migrations against the live PostgreSQL database.
    """

    asyncio.run(
        run_async_migrations()
    )


# ============================================================
# 9. START ALEMBIC
# ============================================================

if context.is_offline_mode():

    run_migrations_offline()

else:

    run_migrations_online()