"""
Pytest configuration and shared fixtures for M1M Sprint 1 tests.

Sets up sys.path, loads .env, and provides an async database session
fixture scoped to the test module.
"""

import sys
from pathlib import Path

# ─── sys.path setup ──────────────────────────────────────────────────────────
# conftest.py is at backend/tests/conftest.py → backend/ is one level up
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

# ─── Load .env ───────────────────────────────────────────────────────────────
_workspace_dir = _backend_dir.parent
for _candidate in (_workspace_dir / ".env", _backend_dir / ".env"):
    if _candidate.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(str(_candidate), override=False)
        except ImportError:
            pass
        break

# ─── App imports ─────────────────────────────────────────────────────────────
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import ssl

from app.config import get_settings
import app.models  # noqa: F401 — register all ORM models


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Async database session scoped to the individual test function.
    Each test gets its own connection to avoid asyncio event loop conflicts.
    """
    settings = get_settings()
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE
    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        connect_args={"ssl": _ssl_ctx},
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()
