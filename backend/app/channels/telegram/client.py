"""
Munim.ai — Telegram Bot API client
====================================
Minimal async client over httpx for the Bot API methods the adapter uses.

Security:
    The bot token is part of every request URL. It is never logged and never
    included in raised errors. httpx logs full request URLs at INFO, so its
    logger is capped at WARNING here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.channels.telegram.types import BotCommand, TelegramUpdate, parse_updates

logger = logging.getLogger(__name__)

# httpx's INFO request log line would contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class TelegramAPIError(Exception):
    """A Bot API call failed. Never carries the token or request URL."""

    def __init__(self, method: str, description: str, error_code: Optional[int] = None):
        self.method = method
        self.description = description
        self.error_code = error_code
        super().__init__(f"Telegram {method} failed ({error_code}): {description}")


class TelegramClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.telegram.org",
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        if not token:
            raise ValueError("Telegram bot token is required.")
        self._base = f"{base_url.rstrip('/')}/bot{token}"
        self._http = http_client or httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _call(
        self,
        method: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        try:
            response = await self._http.post(
                f"{self._base}/{method}",
                json=json,
                data=data,
                files=files,
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.HTTPError as exc:
            # str(exc) can include the URL (and so the token); report the type only.
            raise TelegramAPIError(method, f"network error: {type(exc).__name__}") from None

        try:
            body = response.json()
        except ValueError:
            raise TelegramAPIError(method, f"non-JSON response (HTTP {response.status_code})", response.status_code)

        if not body.get("ok"):
            raise TelegramAPIError(method, body.get("description", "unknown error"), body.get("error_code"))
        return body.get("result")

    # ── Messaging ────────────────────────────────────────────────────────────

    async def send_message(self, chat_id: int, text: str, *, parse_mode: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return await self._call("sendMessage", json=payload)

    async def send_document(
        self,
        chat_id: int,
        path: Path,
        *,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        with open(path, "rb") as fh:
            files = {"document": (filename or path.name, fh.read(), "application/pdf")}
        return await self._call("sendDocument", data=data, files=files, timeout=60.0)

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        await self._call("sendChatAction", json={"chat_id": chat_id, "action": action})

    # ── Updates / webhook management ─────────────────────────────────────────

    async def get_updates(self, *, offset: Optional[int] = None, timeout: int = 30) -> List[TelegramUpdate]:
        payload: Dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        # The HTTP timeout must outlast Telegram's long-poll window.
        result = await self._call("getUpdates", json=payload, timeout=timeout + 15)
        return parse_updates(result or [])

    async def set_webhook(self, url: str, *, secret_token: str, drop_pending_updates: bool = False) -> bool:
        return await self._call("setWebhook", json={
            "url": url,
            "secret_token": secret_token,
            "allowed_updates": ["message"],
            "drop_pending_updates": drop_pending_updates,
        })

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> bool:
        return await self._call("deleteWebhook", json={"drop_pending_updates": drop_pending_updates})

    async def get_webhook_info(self) -> Dict[str, Any]:
        return await self._call("getWebhookInfo")

    async def get_me(self) -> Dict[str, Any]:
        return await self._call("getMe")

    async def set_my_commands(self, commands: List[BotCommand]) -> bool:
        return await self._call("setMyCommands", json={"commands": [c.model_dump() for c in commands]})
