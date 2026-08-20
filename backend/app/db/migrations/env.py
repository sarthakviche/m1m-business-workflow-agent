"""
Alembic migration environment — async SQLAlchemy configuration.

This env.py:
  1. Adds backend/ to sys.path so app.* imports work regardless of CWD.
  2. Loads the .env file from the workspace root before importing app modules.
  3. Reads DATABASE_URL from app.config (never hardcoded here).
  4. Uses async_engine_from_config + asyncio.run() for async SQLAlchemy support.
"""

import asyncio
import ssl
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ─── 1. sys.path: add backend/ so we can import app.* ───────────────────────
# env.py is at:  backend/app/db/migrations/env.py
# backend/ is:   4 parent levels up from env.py
_migrations_dir = Path(__file__).resolve().parent      # backend/app/db/migrations/
_db_dir         = _migrations_dir.parent               # backend/app/db/
_app_dir        = _db_dir.parent                       # backend/app/
_backend_dir    = _app_dir.parent                      # backend/
sys.path.insert(0, str(_backend_dir))

# ─── 2. Load .env before importing app modules ───────────────────────────────
_workspace_dir = _backend_dir.parent                   # m1m/
for _candidate in (_workspace_dir / ".env", _backend_dir / ".env"):
    if _candidate.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(str(_candidate), override=False)
        except ImportError:
            # python-dotenv not installed yet; rely on env vars set in the shell
            pass
        break

# ─── 3. Import app modules (after path + env are ready) ─────────────────────
from app.config import get_settings   # noqa: E402
import app.models                     # noqa: F401, E402 — registers all ORM models
from app.db.base import Base          # noqa: E402

# ─── Alembic config object ───────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Return the async DATABASE_URL from app settings."""
    return get_settings().async_database_url


# ─── Offline mode ────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection (generates SQL script).
    Useful for reviewing changes before applying.
    """
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ─── Online mode (async) ─────────────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine, connect, and run migrations."""
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section, {})
    # Override the placeholder URL from alembic.ini with the real one from env
    configuration["sqlalchemy.url"] = settings.async_database_url

    # Build connect_args based on database type
    _db_url = settings.async_database_url
    _is_sqlite = _db_url.startswith("sqlite+")
    _is_supabase = "supabase" in _db_url.lower()

    _connect_args = {}
    if not _is_sqlite:
        # PostgreSQL-based databases
        if _is_supabase:
            # Supabase uses SSL with a self-signed cert in the chain.
            # We disable hostname verification to work with Supabase's certificate.
            _ssl_ctx = ssl.create_default_context()
            _ssl_ctx.check_hostname = False
            _ssl_ctx.verify_mode = ssl.CERT_NONE
            _connect_args["ssl"] = _ssl_ctx
        # For local PostgreSQL, no SSL is needed

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
