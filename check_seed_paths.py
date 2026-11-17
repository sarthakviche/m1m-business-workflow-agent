import sys
from pathlib import Path

# ─── sys.path setup ──────────────────────────────────────────────────────────
# seed.py is at backend/scripts/seed.py → backend/ is one level up
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

# ─── Load .env from workspace root (m1m/.env) ────────────────────────────────
_workspace_dir = _backend_dir.parent
_env_file = _workspace_dir / ".env"
if not _env_file.exists():
    _env_file = _backend_dir / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_env_file), override=False)
    except ImportError:
        pass  # rely on env vars already exported in the shell

from app.config import get_settings

settings = get_settings()
print(f"CWD: {Path.cwd()}")
print(f"Backend dir: {_backend_dir}")
print(f"Workspace dir: {_workspace_dir}")
print(f"DB URL: {settings.async_database_url}")
