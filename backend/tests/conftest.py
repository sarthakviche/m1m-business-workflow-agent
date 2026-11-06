"""
Pytest configuration and shared fixtures.

The whole suite runs against a throwaway SQLite database built from the real
Alembic migrations and seed script. Tests never touch the developer's m1m.db
or a remote database, and this environment is set before any app import so
cached settings pick it up.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

# ─── sys.path setup ──────────────────────────────────────────────────────────
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

# ─── Test environment (must precede every app import) ────────────────────────
_test_db_dir = Path(tempfile.mkdtemp(prefix="munim-tests-"))
_test_db_file = _test_db_dir / "test.db"
os.environ["ENV"] = "development"
# TEST_DATABASE_URL runs the suite on a real, disposable Postgres (as CI does).
# Everything in that database may be overwritten.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{_test_db_file.as_posix()}"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SPRINT_TENANT_ID"] = ""
os.environ["MUNIM_API_KEYS"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_JWT_SECRET"] = ""
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_WEBHOOK_SECRET"] = ""

# Tests are offline by default, so CI needs no secrets and spends no AI quota.
# RUN_LIVE_GEMINI=1 adds the smoke test, using the real key from .env.
_live_gemini = os.environ.get("RUN_LIVE_GEMINI") == "1"
if not _live_gemini:
    os.environ["GEMINI_API_KEY"] = ""
collect_ignore = [] if _live_gemini else ["test_gemini_smoke.py"]

# ─── App imports ─────────────────────────────────────────────────────────────
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
import app.models  # noqa: F401 — register all ORM models


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """Build the schema from migrations (so they are tested too), then seed it."""
    config = Config(str(_backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(_backend_dir / "app" / "db" / "migrations"))
    command.upgrade(config, "head")

    from scripts.seed import seed
    asyncio.run(seed())

    yield

    shutil.rmtree(_test_db_dir, ignore_errors=True)


@pytest_asyncio.fixture(autouse=True)
async def _release_app_connections():
    """Each test has its own event loop, and Postgres connections can't outlive theirs."""
    yield
    from app.db.session import engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Async session per test, on its own connection to avoid event loop conflicts."""
    engine = create_async_engine(get_settings().async_database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
