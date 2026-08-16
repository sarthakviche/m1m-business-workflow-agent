"""
Async SQLAlchemy engine and session factory.

IMPORTANT:
  - Schema is managed exclusively by Alembic migrations.
  - create_all() / drop_all() are NEVER called here.
  - SSL is enabled for Supabase (self-signed cert chain — verification disabled).
"""

import ssl

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_settings = get_settings()

# Supabase uses SSL with a self-signed certificate in the chain.
# We disable hostname/cert verification to connect successfully.
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    _settings.async_database_url,
    # Enable SQL echo only in development — never in production
    echo=_settings.env == "development",
    connect_args={"ssl": _ssl_ctx},
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
