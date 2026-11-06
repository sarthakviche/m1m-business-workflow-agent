"""
Munim.ai — Price-list import over Telegram
===========================================
    photo / PDF / CSV → download → extract_catalog (same checks as the web app)
        → numbered summary + inline buttons → [pick GST] → Save → apply_catalog_import

Nothing is written to the catalog until the owner taps Save. Rows without a
price are listed but never saved (the bot has no way to type one in; the web
importer does). Items the owner wants to edit row by row are pointed to the
web app.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.channels.pending_import import PendingImport, PendingRow, import_key, pending_imports
from app.channels.telegram.client import TelegramAPIError, TelegramClient
from app.channels.telegram.types import TelegramCallbackQuery, TelegramMessage
from app.errors.categories import MunimError
from app.services.catalog_import import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_MIME_TYPES,
    apply_catalog_import,
    extract_catalog,
)

logger = logging.getLogger(__name__)

CHANNEL = "telegram"
CALLBACK_PREFIX = "imp"

# Offered when the sheet doesn't print a GST rate. Other slabs: use the web importer.
GST_CHOICES = ("0", "5", "12", "18", "28", "40")
# Rows listed in the summary; the rest are counted (and still saved).
MAX_LISTED_ROWS = 40

READING_TEXT = "📄 Got it. Reading your price list, this takes about 15 seconds…"
UNSUPPORTED_FILE_TEXT = "I can read price lists sent as a photo, a PDF or a CSV file."
TOO_LARGE_TEXT = "That file is over 10 MB. Send a smaller photo, or split the PDF."
DOWNLOAD_FAILED_TEXT = "I couldn't download that file from Telegram. Please send it again."
EXPIRED_TEXT = "That import has expired or was already handled. Send the price list again to start over."
WEB_EDIT_HINT = "To change individual rows, use **Stock → Import price list** in the web app."

Reply = Callable[..., Awaitable[Optional[Dict[str, Any]]]]


def _display(name: str) -> str:
    # Keep item names from being read as Markdown: "12*100" is a size, not bold.
    return name.replace("`", "'").replace("*", "×")


def _money(value: str) -> str:
    return f"₹{Decimal(value):,.2f}"


def _rate(value: str) -> str:
    return f"{Decimal(value).normalize():f}%"


def _row_line(index: int, row: PendingRow) -> str:
    name = _display(row.name)
    if not row.has_price:
        return f"{index}. ⚠️ {name}: no price on the list, will be skipped"
    parts = [f"{_money(row.unit_price)}/{row.unit}",
             f"GST {_rate(row.gst_rate_percent)}" if row.gst_rate_percent else "GST ?"]
    if row.quantity_available is not None:
        parts.append(f"stock {Decimal(row.quantity_available).normalize():f}")
    if row.match == "update" and row.existing_unit_price is not None:
        parts.append(f"_updates {_money(row.existing_unit_price)}_")
    elif row.match == "unchanged":
        parts.append("_already saved_")
    else:
        parts.append("_new_")
    return f"{index}. {name}: " + " · ".join(parts)


def summary_text(pending: PendingImport, *, with_status: bool = True) -> str:
    rows = pending.rows
    lines = [f"📋 **Found {len(rows)} item{'s' if len(rows) != 1 else ''}** on your list:", ""]
    lines += [_row_line(i, r) for i, r in enumerate(rows[:MAX_LISTED_ROWS], start=1)]
    if len(rows) > MAX_LISTED_ROWS:
        lines.append(f"…and {len(rows) - MAX_LISTED_ROWS} more.")
    lines.append("")
    if pending.notes:
        lines.append(f"Note: {pending.notes}")
    if with_status:
        lines += _status_lines(pending)
    return "\n".join(lines).rstrip()


def _status_lines(pending: PendingImport) -> List[str]:
    lines: List[str] = []
    no_price = sum(1 for r in pending.rows if not r.has_price)
    unchanged = sum(1 for r in pending.rows if r.match == "unchanged")
    needs_gst = len(pending.rows_needing_gst)
    if no_price:
        lines.append(f"{no_price} item{' has' if no_price == 1 else 's have'} no price and will be skipped.")
    if unchanged:
        lines.append(f"{unchanged} item{' is' if unchanged == 1 else 's are'} already up to date.")
    if needs_gst:
        lines.append(f"⚠️ **{needs_gst} item{' has' if needs_gst == 1 else 's have'} no GST rate.** "
                     "Pick the rate for them below.")
    elif pending.savable_rows:
        lines.append("Check the list against your sheet. Nothing is saved until you tap **Save**.")
    lines.append(WEB_EDIT_HINT)
    return lines


def keyboard(pending: PendingImport) -> Dict[str, Any]:
    token = pending.token
    rows: List[List[Dict[str, str]]] = []
    if pending.rows_needing_gst:
        buttons = [{"text": f"GST {r}%", "callback_data": f"{CALLBACK_PREFIX}:gst{r}:{token}"} for r in GST_CHOICES]
        rows += [buttons[:3], buttons[3:]]
    else:
        count = len(pending.savable_rows)
        rows.append([{"text": f"✅ Save {count} item{'s' if count != 1 else ''}",
                      "callback_data": f"{CALLBACK_PREFIX}:save:{token}"}])
    rows.append([{"text": "✖️ Discard", "callback_data": f"{CALLBACK_PREFIX}:discard:{token}"}])
    return {"inline_keyboard": rows}


def _file_to_read(message: TelegramMessage):
    """(file_id, mime_type, size) for the photo or document in a message, or None."""
    if message.photo:
        largest = max(message.photo, key=lambda p: p.width * p.height)
        return largest.file_id, "image/jpeg", largest.file_size
    doc = message.document
    if doc is not None:
        mime = (doc.mime_type or "").lower()
        if not mime and (doc.file_name or "").lower().endswith(".csv"):
            mime = "text/csv"
        return doc.file_id, mime, doc.file_size
    return None


def is_import_message(message: TelegramMessage) -> bool:
    return bool(message.photo) or message.document is not None


class TelegramCatalogImport:
    def __init__(
        self,
        client: TelegramClient,
        session_factory: async_sessionmaker[AsyncSession],
        reply: Reply,
    ):
        self.client = client
        self._session_factory = session_factory
        self._reply = reply

    # ── Incoming file ────────────────────────────────────────────────────────

    async def handle_file(self, message: TelegramMessage, tenant_id: uuid.UUID) -> None:
        chat_id = message.chat.id
        file_id, mime, size = _file_to_read(message)
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime not in SUPPORTED_MIME_TYPES:
            await self._reply(chat_id, UNSUPPORTED_FILE_TEXT)
            return
        if size and size > MAX_UPLOAD_BYTES:
            await self._reply(chat_id, TOO_LARGE_TEXT)
            return

        await self._reply(chat_id, READING_TEXT)
        try:
            await self.client.send_chat_action(chat_id, "typing")
        except TelegramAPIError:
            pass  # cosmetic only
        try:
            content = await self.client.download_file(file_id, max_bytes=MAX_UPLOAD_BYTES)
        except TelegramAPIError as exc:
            await self._reply(chat_id, TOO_LARGE_TEXT if exc.error_code == 413 else DOWNLOAD_FAILED_TEXT)
            return

        key = import_key(CHANNEL, tenant_id, chat_id)
        async with self._session_factory() as session:
            try:
                preview = await extract_catalog(session, tenant_id, content, mime)
            except MunimError as exc:
                logger.info("telegram.import.extract_failed", extra={"code": exc.code})
                await self._reply(chat_id, exc.user_message)
                return

            if not preview.rows:
                await pending_imports.clear(session, key)
                await session.commit()
                note = f"\n\n{preview.notes}" if preview.notes else ""
                await self._reply(chat_id, "I couldn't find any items with prices in that file. "
                                           f"Try a sharper photo with the whole list in frame.{note}")
                return

            previous = await pending_imports.get(session, key, tenant_id)
            pending = PendingImport.from_preview(preview)
            if not pending.savable_rows and not pending.rows_needing_gst:
                await pending_imports.clear(session, key)
                await session.commit()
                await self._reply(chat_id, summary_text(pending, with_status=False)
                                  + "\n\nThere's nothing new to save from this list.")
                await self._strip_buttons(chat_id, previous)
                return

            await pending_imports.save(session, key, tenant_id, pending)
            await session.commit()

        logger.info("telegram.import.preview", extra={"rows": len(pending.rows)})
        await self._strip_buttons(chat_id, previous)
        await self._send_with_keyboard(chat_id, tenant_id, pending, summary_text(pending))

    # ── Button taps ──────────────────────────────────────────────────────────

    async def handle_callback(self, query: TelegramCallbackQuery, tenant_id: uuid.UUID) -> None:
        chat_id = query.message.chat.id
        parts = (query.data or "").split(":", 2)
        if len(parts) != 3:
            await self._answer(query)
            return
        _, action, token = parts
        key = import_key(CHANNEL, tenant_id, chat_id)

        async with self._session_factory() as session:
            pending = await pending_imports.get(session, key, tenant_id)
            if pending is None or pending.token != token:
                await self._answer(query, "This import has expired.")
                await self._safe_remove_keyboard(chat_id, query.message.message_id)
                await self._reply(chat_id, EXPIRED_TEXT)
                return

            if action == "discard":
                await pending_imports.clear(session, key)
                await session.commit()
                await self._answer(query, "Discarded")
                await self._strip_buttons(chat_id, pending)
                await self._reply(chat_id, "Okay, I've discarded that price list. Nothing was saved.")
                return

            if action.startswith("gst") and action[3:] in GST_CHOICES:
                count = pending.apply_gst(Decimal(action[3:]))
                await pending_imports.save(session, key, tenant_id, pending)
                await session.commit()
                await self._answer(query, f"GST {action[3:]}% applied")
                await self._strip_buttons(chat_id, pending)
                pending.source_message_ids = []
                text = (f"Set **GST {action[3:]}%** on {count} item{'s' if count != 1 else ''}.\n"
                        + "\n".join(_status_lines(pending)))
                await self._send_with_keyboard(chat_id, tenant_id, pending, text)
                return

            if action == "save":
                rows = pending.savable_rows
                if not rows:
                    await self._answer(query)
                    await self._reply(chat_id, "There's nothing to save from this list.")
                    return
                result = await apply_catalog_import(session, tenant_id, [r.to_import_row() for r in rows])
                await pending_imports.clear(session, key)
                await session.commit()
                await self._answer(query, "Saved")
                await self._strip_buttons(chat_id, pending)
                logger.info("telegram.import.saved", extra={"created": result.created, "updated": result.updated})
                done = [f"{result.created} added"] if result.created else []
                if result.updated:
                    done.append(f"{result.updated} updated")
                if result.unchanged:
                    done.append(f"{result.unchanged} already up to date")
                lines = [f"✅ **Catalog updated:** {', '.join(done) or 'no changes'}."]
                skipped = sum(1 for r in pending.rows if not r.has_price)
                if skipped:
                    lines.append(f"{skipped} item{'s' if skipped != 1 else ''} without a price "
                                 f"{'were' if skipped != 1 else 'was'} skipped.")
                lines.append(f"\nYou can quote them now, e.g. _Quotation for Ramesh Traders, 10 {_display(rows[0].name)}_")
                await self._reply(chat_id, "\n".join(lines))
                return

        await self._answer(query)

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _send_with_keyboard(self, chat_id: int, tenant_id: uuid.UUID, pending: PendingImport, text: str) -> None:
        sent = await self._reply(chat_id, text, reply_markup=keyboard(pending))
        if sent and sent.get("message_id"):
            pending.source_message_ids.append(sent["message_id"])
            async with self._session_factory() as session:
                key = import_key(CHANNEL, tenant_id, chat_id)
                current = await pending_imports.get(session, key, tenant_id)
                if current is not None and current.token == pending.token:
                    current.source_message_ids = pending.source_message_ids
                    await pending_imports.save(session, key, tenant_id, current)
                    await session.commit()

    async def _strip_buttons(self, chat_id: int, pending: Optional[PendingImport]) -> None:
        for message_id in (pending.source_message_ids if pending else []):
            await self._safe_remove_keyboard(chat_id, message_id)

    async def _safe_remove_keyboard(self, chat_id: int, message_id: int) -> None:
        try:
            await self.client.remove_inline_keyboard(chat_id, message_id)
        except TelegramAPIError:
            pass  # already removed, or the message is too old to edit

    async def _answer(self, query: TelegramCallbackQuery, text: Optional[str] = None) -> None:
        try:
            await self.client.answer_callback_query(query.id, text)
        except TelegramAPIError:
            pass  # the spinner times out on its own
