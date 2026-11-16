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


# Update types the bot subscribes to (messages and inline-button taps).
ALLOWED_UPDATES = ["message", "callback_query"]


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
        self._file_base = f"{base_url.rstrip('/')}/file/bot{token}"
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

    async def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return await self._call("sendMessage", json=payload)

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> None:
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        await self._call("answerCallbackQuery", json=payload)

    async def remove_inline_keyboard(self, chat_id: int, message_id: int) -> None:
        await self._call("editMessageReplyMarkup", json={
            "chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []},
        })

    async def send_document(
        self,
        chat_id: int,
        content: bytes,
        *,
        filename: str = "document.pdf",
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        files = {"document": (filename, content, "application/pdf")}
        return await self._call("sendDocument", data=data, files=files, timeout=60.0)

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        await self._call("sendChatAction", json={"chat_id": chat_id, "action": action})

    # ── Files ────────────────────────────────────────────────────────────────

    async def download_file(self, file_id: str, *, max_bytes: int) -> bytes:
        """Download a file a user sent. Raises TelegramAPIError if it is missing or over max_bytes."""
        info = await self._call("getFile", json={"file_id": file_id})
        file_path = (info or {}).get("file_path")
        if not file_path:
            raise TelegramAPIError("getFile", "no file_path (file may be over 20 MB)")
        if (info.get("file_size") or 0) > max_bytes:
            raise TelegramAPIError("getFile", "file too large", 413)
        try:
            response = await self._http.get(f"{self._file_base}/{file_path}", timeout=60.0)
        except httpx.HTTPError as exc:
            raise TelegramAPIError("downloadFile", f"network error: {type(exc).__name__}") from None
        if response.status_code != 200:
            raise TelegramAPIError("downloadFile", f"HTTP {response.status_code}", response.status_code)
        if len(response.content) > max_bytes:
            raise TelegramAPIError("downloadFile", "file too large", 413)
        return response.content

    # ── Updates / webhook management ─────────────────────────────────────────

    async def get_updates(self, *, offset: Optional[int] = None, timeout: int = 30) -> List[TelegramUpdate]:
        payload: Dict[str, Any] = {"timeout": timeout, "allowed_updates": ALLOWED_UPDATES}
        if offset is not None:
            payload["offset"] = offset
        # The HTTP timeout must outlast Telegram's long-poll window.
        result = await self._call("getUpdates", json=payload, timeout=timeout + 15)
        return parse_updates(result or [])

    async def set_webhook(self, url: str, *, secret_token: str, drop_pending_updates: bool = False) -> bool:
        return await self._call("setWebhook", json={
            "url": url,
            "secret_token": secret_token,
            "allowed_updates": ALLOWED_UPDATES,
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
