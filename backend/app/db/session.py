"""
db/session.py — Async SQLAlchemy engine + session factory.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ---------------------------------------------------------
# BASE MODEL
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# DATABASE URL
# ---------------------------------------------------------

database_url = settings.database_url

# Make sure SQLAlchemy uses asyncpg
if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )


# ---------------------------------------------------------
# DATABASE ENGINE
# ---------------------------------------------------------

engine = create_async_engine(
    database_url,
    echo=(settings.env == "development"),
    pool_pre_ping=True,

    # IMPORTANT FOR SUPABASE PGBOUNCER
    connect_args={
        "statement_cache_size": 0,
    },
)


# ---------------------------------------------------------
# SESSION FACTORY
# ---------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------------------------------------------------------
# DATABASE DEPENDENCY
# ---------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI database dependency.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session

        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------
# TENANT / RLS CONTEXT
# ---------------------------------------------------------

async def set_tenant_context(
    session: AsyncSession,
    tenant_id: UUID | str,
) -> None:
    """
    Set the PostgreSQL tenant context used by RLS policies.
    """

    await session.execute(
        text(
            "SELECT set_config("
            "'app.current_tenant_id', "
            ":tenant_id, "
            "false"
            ")"
        ),
        {
            "tenant_id": str(tenant_id),
        },
    )


# ---------------------------------------------------------
# TENANT-SCOPED SESSION
# ---------------------------------------------------------

@asynccontextmanager
async def get_tenant_session(
    tenant_id: UUID | str,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session with tenant context already set.
    """

    async with AsyncSessionLocal() as session:

        async with session.begin():

            await set_tenant_context(
                session,
                tenant_id,
            )

            yield session


# ---------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------

async def close_db() -> None:
    """
    Dispose the SQLAlchemy engine.
    """

    await engine.dispose()