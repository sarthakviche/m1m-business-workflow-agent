"""
M1M (Munim.ai) — Application Configuration
=============================================
Loads all settings from environment variables (and optionally a .env file).

Security rules (non-negotiable):
  - Database credentials are NEVER hardcoded here.
  - Secrets come exclusively from environment variables / .env file.
  - .env is always gitignored — never committed.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Sprint 1 dev fallback UUID ──────────────────────────────────────────────
# Used ONLY when SPRINT_TENANT_ID env var is not set.
# This is a clearly fictional UUID for local development/testing.
# NEVER use this in a real/production environment.
SPRINT_TENANT_ID_DEFAULT = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def _find_env_file() -> str:
    """
    Walk up from CWD (up to 5 levels) to find a .env file.
    This lets the app find the .env at the workspace root regardless of
    which directory alembic / pytest / seed.py is invoked from.
    """
    current = Path.cwd()
    for _ in range(5):
        candidate = current / ".env"
        if candidate.exists():
            return str(candidate)
        current = current.parent
    return ".env"  # pydantic-settings silently ignores a missing env_file


def _find_workspace_root() -> Path:
    """
    Find the workspace root by walking up until we find .env or .git.
    This is more reliable than using Path.cwd().
    """
    current = Path.cwd()
    for _ in range(5):
        if (current / ".env").exists() or (current / ".git").exists():
            return current
        current = current.parent
    # Fallback: return current directory
    return current


def _normalize_db_url(url: str) -> str:
    """
    Normalise DATABASE_URL to use postgresql+asyncpg:// scheme.

    Also handles literal bracket characters [ ] in the password portion —
    these are not valid URL characters and must be percent-encoded before
    SQLAlchemy's URL parser sees them, otherwise the password is truncated
    at the bracket.

    Accepts:
      postgresql://...           (Supabase dashboard default)
      postgres://...             (Heroku-style)
      postgresql+asyncpg://...   (already correct — no-op)
    """
    url = url.strip()

    # ── 1. Normalise scheme ──────────────────────────────────────────────────
    if url.startswith("postgresql+asyncpg://") or url.startswith("postgres+asyncpg://"):
        normalised = url
    elif url.startswith("postgresql://"):
        normalised = "postgresql+asyncpg://" + url[len("postgresql://"):]
    elif url.startswith("postgres://"):
        normalised = "postgresql+asyncpg://" + url[len("postgres://"):]
    else:
        return url  # return unchanged; SQLAlchemy will raise on invalid URL

    # ── 2. Percent-encode literal brackets in the credentials section ────────
    # Structure: scheme://[user[:password]@]host[:port]/database[?params]
    # We must only encode brackets that appear BEFORE the last @ (credentials),
    # not after it (host/path).
    try:
        scheme_end = normalised.index("://") + 3          # position after ://
        at_pos = normalised.rfind("@")                    # last @ = cred/host boundary
        if at_pos > scheme_end:
            creds = normalised[scheme_end:at_pos]         # e.g. user:p%40ssword[extra]
            rest = normalised[at_pos:]                    # @host:port/db
            # Encode literal [ and ] which are reserved for IPv6 host notation
            creds_encoded = creds.replace("[", "%5B").replace("]", "%5D")
            normalised = normalised[:scheme_end] + creds_encoded + rest
    except (ValueError, IndexError):
        pass  # URL has no @ (no credentials) — leave as-is

    return normalised


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All secrets must come from the environment — no hardcoded values.
    
    Supports multiple database backends:
      - supabase: Remote PostgreSQL (via Supabase)
      - local_postgres: Local PostgreSQL on localhost:5432
      - sqlite: SQLite file (local development, no external dependencies)
    """

    database_url: Optional[str] = None
    db_environment: str = "sqlite"  # Default to SQLite for zero-config dev
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "m1m_local"
    db_user: str = "postgres"
    db_password: str = "postgres"
    env: str = "development"
    sprint_tenant_id: str = ""

    # ── Gemini AI (Sprint 1 Step 2+) ──────────────────────────────────────────
    # Set GEMINI_API_KEY in your .env file.  Never hardcode or log this value.
    gemini_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """
        Resolves the final database URL based on DB_ENVIRONMENT setting.
        
        Priority:
          1. If DATABASE_URL is explicitly set → use it (backward compatibility)
          2. If DB_ENVIRONMENT is set → generate URL from config
          3. Default → SQLite (zero-config development)
        """
        # Backward compatibility: if DATABASE_URL is explicitly set, use it
        if self.database_url and self.database_url.strip():
            return _normalize_db_url(self.database_url)
        
        # Generate URL based on DB_ENVIRONMENT
        env = (self.db_environment or "").strip().lower()
        
        if env == "supabase":
            # Expect DATABASE_URL to be set for Supabase
            if self.database_url and self.database_url.strip():
                return _normalize_db_url(self.database_url)
            raise ValueError(
                "DB_ENVIRONMENT=supabase requires DATABASE_URL to be set in .env"
            )
        
        elif env == "local_postgres":
            # Build PostgreSQL connection string from components
            url = f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
            return url
        
        elif env == "sqlite":
            # SQLite connection string (file-based, local)
            # Always store at workspace_root/m1m.db regardless of CWD
            workspace_root = _find_workspace_root()
            db_file = workspace_root / "m1m.db"
            return f"sqlite+aiosqlite:///{db_file}"
        
        else:
            raise ValueError(
                f"Invalid DB_ENVIRONMENT: {env}. "
                "Must be one of: 'supabase', 'local_postgres', 'sqlite'"
            )

    @property
    def effective_sprint_tenant_id(self) -> str:
        """
        Returns the Sprint 1 tenant UUID.
        Uses SPRINT_TENANT_ID from the environment if set and non-empty,
        otherwise falls back to the documented dev UUID.
        """
        tid = (self.sprint_tenant_id or "").strip()
        return tid if tid else SPRINT_TENANT_ID_DEFAULT


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — safe to call anywhere."""
    return Settings()
