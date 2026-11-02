"""
M1M (Munim.ai) — Telegram bot operations CLI
==============================================
Usage (from the repository root):
  python backend/scripts/telegram_bot.py poll
      Local development: removes any webhook and long-polls Telegram, feeding
      updates through the same handler the production webhook uses.

  python backend/scripts/telegram_bot.py link-code [--tenant-id UUID]
      Issues a one-time code. Send "/link CODE" to the bot to link your chat.
      Defaults to the sprint tenant (SPRINT_TENANT_ID or the dev tenant).

  python backend/scripts/telegram_bot.py set-webhook https://api.example.com
      Production: points Telegram at <base>/api/v1/telegram/webhook using
      TELEGRAM_WEBHOOK_SECRET, and registers the bot's command menu.

  python backend/scripts/telegram_bot.py delete-webhook
  python backend/scripts/telegram_bot.py webhook-info

Requires TELEGRAM_BOT_TOKEN in .env and `alembic upgrade head` to have run.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import timedelta
from pathlib import Path

# ─── sys.path + .env setup (same as seed.py) ─────────────────────────────────
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))
_workspace_dir = _backend_dir.parent
_env_file = _workspace_dir / ".env"
if not _env_file.exists():
    _env_file = _backend_dir / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_env_file), override=False)
    except ImportError:
        pass

import app.models  # noqa: E402,F401 — register all ORM models
from app.channels.linking import create_link_code  # noqa: E402
from app.channels.telegram.client import TelegramAPIError, TelegramClient  # noqa: E402
from app.channels.telegram.handler import BOT_COMMANDS, TelegramUpdateHandler  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402

logger = logging.getLogger("telegram_bot")

WEBHOOK_PATH = "/api/v1/telegram/webhook"


def _client() -> TelegramClient:
    settings = get_settings()
    if not settings.telegram_bot_token:
        sys.exit("TELEGRAM_BOT_TOKEN is not set. Create a bot with @BotFather and add the token to .env.")
    return TelegramClient(settings.telegram_bot_token, base_url=settings.telegram_api_base_url)


async def poll() -> None:
    client = _client()
    me = await client.get_me()
    await client.delete_webhook(drop_pending_updates=False)
    await client.set_my_commands(BOT_COMMANDS)
    handler = TelegramUpdateHandler(client, AsyncSessionLocal)
    print(f"Polling as @{me.get('username')} — press Ctrl+C to stop.", flush=True)

    offset = None
    backoff = 1
    try:
        while True:
            try:
                updates = await client.get_updates(offset=offset, timeout=30)
                backoff = 1
            except TelegramAPIError as exc:
                logger.warning("getUpdates failed: %s (retrying in %ss)", exc.description, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            for update in updates:
                offset = update.update_id + 1
                await handler.handle(update)
    finally:
        await client.aclose()


async def link_code(tenant_id: str | None) -> None:
    settings = get_settings()
    tenant = uuid.UUID(tenant_id or settings.effective_sprint_tenant_id)
    async with AsyncSessionLocal() as session:
        issued = await create_link_code(
            session, tenant, "telegram", timedelta(minutes=settings.telegram_link_code_ttl_minutes)
        )
        await session.commit()

    deep_link = ""
    if settings.telegram_bot_token:
        client = _client()
        try:
            username = (await client.get_me()).get("username")
            deep_link = f"\nOr open: https://t.me/{username}?start={issued.code}"
        except TelegramAPIError:
            pass
        finally:
            await client.aclose()
    print(
        f"Link code for tenant {tenant}: {issued.code}\n"
        f"Expires at {issued.expires_at:%Y-%m-%d %H:%M} UTC. Send to the bot: /link {issued.code}{deep_link}"
    )


async def set_webhook(base_url: str, drop_pending: bool) -> None:
    secret = get_settings().telegram_webhook_secret
    if not secret:
        sys.exit("TELEGRAM_WEBHOOK_SECRET is not set. Generate one, e.g.: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    if not base_url.startswith("https://"):
        sys.exit("Telegram only delivers webhooks to https:// URLs.")
    client = _client()
    try:
        url = base_url.rstrip("/") + WEBHOOK_PATH
        await client.set_webhook(url, secret_token=secret, drop_pending_updates=drop_pending)
        await client.set_my_commands(BOT_COMMANDS)
        print(f"Webhook set to {url}")
    finally:
        await client.aclose()


async def delete_webhook() -> None:
    client = _client()
    try:
        await client.delete_webhook()
        print("Webhook deleted.")
    finally:
        await client.aclose()


async def webhook_info() -> None:
    client = _client()
    try:
        info = await client.get_webhook_info()
        for key in ("url", "pending_update_count", "last_error_date", "last_error_message"):
            print(f"{key}: {info.get(key)}")
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Munim Telegram bot operations")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("poll", help="Long-poll Telegram (local development)")
    p_link = sub.add_parser("link-code", help="Issue a one-time chat link code")
    p_link.add_argument("--tenant-id", default=None)
    p_hook = sub.add_parser("set-webhook", help="Point Telegram at this deployment")
    p_hook.add_argument("base_url", help="Public https base URL of the API")
    p_hook.add_argument("--drop-pending", action="store_true")
    sub.add_parser("delete-webhook")
    sub.add_parser("webhook-info")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # The dev engine echoes every SQL statement; keep the bot console readable.
    engine.echo = False

    commands = {
        "poll": lambda: poll(),
        "link-code": lambda: link_code(args.tenant_id),
        "set-webhook": lambda: set_webhook(args.base_url, args.drop_pending),
        "delete-webhook": lambda: delete_webhook(),
        "webhook-info": lambda: webhook_info(),
    }
    try:
        asyncio.run(commands[args.command]())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
