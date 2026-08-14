"""
db/session.py — Async SQLAlchemy engine + session factory.

Critical: every request must call `set_tenant_context(session, tenant_id)` BEFORE
any query executes. This sets the Postgres session parameter `app.current_tenant_id`
which the RLS policies rely on. Sourced from the authenticated user's JWT — NEVER
from a client-supplied header or query param.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings


# Engine — echo=True only in development for query logging
engine = create_async_engine(
    settings.database_url,
    echo=(settings.env == "development"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | str) -> None:
    """
    Set the RLS context variable for the current DB session.

    This must be called at the start of EVERY tenant-scoped request, using the
    tenant_id extracted from the validated JWT — not from any client input.

    Uses SET LOCAL so the setting is scoped to the current transaction only.
    """
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )


@asynccontextmanager
async def get_tenant_session(tenant_id: UUID | str) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager: yields an AsyncSession already scoped to the given tenant.
    Use this in agent tools and service functions that receive tenant_id from auth.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, tenant_id)
            yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields a bare session (no RLS context set yet).
    Caller must set RLS context via the `require_tenant` dependency before querying.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
