"""
Async SQLAlchemy engine and session factory.

IMPORTANT:
  - Schema is managed exclusively by Alembic migrations.
  - create_all() / drop_all() are NEVER called here.
  - SSL is enabled for Supabase (self-signed cert chain — verification disabled).
  - SQLite and local PostgreSQL do not use SSL.
"""

import ssl
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_settings = get_settings()
_db_url = _settings.async_database_url
_is_sqlite = _db_url.startswith("sqlite+")
_is_supabase = "supabase" in _db_url.lower()

# Build connection arguments based on database type
_connect_args: Dict[str, Any] = {}

if not _is_sqlite:
    # PostgreSQL-based databases
    if _is_supabase:
        # Supabase uses SSL with a self-signed certificate in the chain.
        # We disable hostname/cert verification to connect successfully.
        _ssl_ctx = ssl.create_default_context()
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = ssl.CERT_NONE
        _connect_args["ssl"] = _ssl_ctx
    # For local PostgreSQL, no SSL is needed

engine = create_async_engine(
    _db_url,
    # Enable SQL echo only in development — never in production
    echo=_settings.env == "development",
    connect_args=_connect_args,
    # Connection pool settings suitable for a low-traffic dev environment
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # test connections before using them from the pool
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
