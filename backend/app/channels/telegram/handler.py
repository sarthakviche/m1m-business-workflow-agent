"""
Munim.ai — Telegram update handler
====================================
Processes one Telegram update end to end:

    update → private-chat filter → dedup claim (update_id) → per-chat lock
           → /command      : handled deterministically (no LLM)
           → photo / file  : price-list import, saved only after a button tap
                             (see catalog_import.py)
           → button tap    : import actions (set GST, save, discard)
           → free text     : linked identity → tenant → server-side history
                             → MunimOrchestrator → commit → reply (+ PDF)

Invariants:
    - The tenant comes only from the linked ChannelIdentity.
    - Unlinked chats never reach the orchestrator.
    - The reply is sent only after the database transaction commits, so the
      bot never announces a document that was rolled back.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import weakref
from typing import Any, Awaitable, Callable, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.channels import linking
from app.channels.inbound_events import claim_event
from app.channels.telegram.catalog_import import CALLBACK_PREFIX, TelegramCatalogImport, is_import_message
from app.channels.telegram.client import TelegramAPIError, TelegramClient
from app.channels.telegram.formatting import split_message, to_plain_text, to_telegram_html
from app.channels.telegram.types import BotCommand, TelegramCallbackQuery, TelegramMessage, TelegramUpdate
from app.conversation.history import load_recent_history
from app.conversation.store import conversation_store
from app.models.tenant import Tenant
from app.orchestrator.context import RequestContext
from app.orchestrator.message import NormalizedMessage
from app.orchestrator.orchestrator import MunimOrchestrator, get_orchestrator
from app.services.document_lookup import DocumentSummary, find_document_by_number, list_recent_documents
from app.services.pdf_service import load_pdf

logger = logging.getLogger(__name__)

CHANNEL = "telegram"

# Fixed namespace so each (tenant, chat) maps to the same conversation_id forever.
_CONVERSATION_NAMESPACE = uuid.UUID("6f1d3c52-8a4e-4b7f-9c1e-2d5a7b9e0f13")

BOT_COMMANDS = [
    BotCommand(command="help", description="What I can do"),
    BotCommand(command="quotations", description="Your 5 most recent quotations"),
    BotCommand(command="invoices", description="Your 5 most recent invoices"),
    BotCommand(command="pdf", description="Get a document PDF, e.g. /pdf Q-202611-001"),
    BotCommand(command="cancel", description="Discard the request in progress"),
    BotCommand(command="link", description="Link this chat with a code"),
    BotCommand(command="unlink", description="Disconnect this chat"),
]

HELP_TEXT = (
    "I'm **Munim**, your business assistant. Just type what you need:\n"
    "• _Create a quotation for Ramesh Traders, 10 TMT Steel Rod 12mm_\n"
    "• _Make an invoice for Q-202611-001_\n"
    "• _What's the price and stock of MS Hex Bolt?_\n"
    "• Send a **photo of your price list** (or a PDF/CSV) to add items to your catalog\n\n"
    "Commands:\n"
    "/quotations — recent quotations\n"
    "/invoices — recent invoices\n"
    "/pdf NUMBER — get a document PDF\n"
    "/cancel — discard the request in progress\n"
    "/unlink — disconnect this chat"
)
NOT_LINKED_TEXT = (
    "This chat isn't linked to a business yet.\n\n"
    "Ask your Munim admin for a link code, then send:\n"
    "`/link YOUR-CODE`"
)
LINK_FAILED_TEXT = "That link code is invalid, expired or already used. Please ask for a new one."
TEXT_ONLY_TEXT = "I can read text messages, and photos, PDFs or CSVs of your price list. Please type your request."
ERROR_TEXT = "Something went wrong on my side. Please try again in a moment."

_DOC_LABELS = {"quotation": "quotations", "invoice": "invoices"}


def conversation_id_for(tenant_id: uuid.UUID, chat_id: int) -> uuid.UUID:
    return uuid.uuid5(_CONVERSATION_NAMESPACE, f"{CHANNEL}:{tenant_id}:{chat_id}")


def _format_document_line(doc: DocumentSummary) -> str:
    date = doc.created_at.strftime("%d %b %Y") if doc.created_at else ""
    return f"• **{doc.number}** — {doc.customer_name} — ₹{doc.total:,.2f} — {doc.status} — {date}"


class TelegramUpdateHandler:
    def __init__(
        self,
        client: TelegramClient,
        session_factory: async_sessionmaker[AsyncSession],
        orchestrator: Optional[MunimOrchestrator] = None,
    ):
        self.client = client
        self._session_factory = session_factory
        self._orchestrator = orchestrator or get_orchestrator()
        # Serialize messages per chat so multi-turn state is never raced.
        # Single-process guarantee; across workers the DB state still applies.
        self._chat_locks: "weakref.WeakValueDictionary[int, asyncio.Lock]" = weakref.WeakValueDictionary()
        self._catalog_import = TelegramCatalogImport(client, session_factory, self.reply)
        self._commands: Dict[str, Callable[[TelegramMessage, str], Awaitable[None]]] = {
            "start": self._cmd_start,
            "link": self._cmd_link,
            "unlink": self._cmd_unlink,
            "help": self._cmd_help,
            "quotations": self._cmd_quotations,
            "invoices": self._cmd_invoices,
            "pdf": self._cmd_pdf,
            "cancel": self._cmd_cancel,
        }

    async def handle(self, update: TelegramUpdate) -> None:
        query = update.callback_query
        message = query.message if query is not None else update.message
        user = query.from_user if query is not None else (message.from_user if message else None)
        if message is None or user is None or user.is_bot:
            return
        if message.chat.type != "private":
            # Group chats would expose one business's documents to every member.
            return
        if not await claim_event(self._session_factory, CHANNEL, str(update.update_id)):
            logger.info("telegram.update.duplicate", extra={"update_id": update.update_id})
            return

        lock = self._chat_locks.get(message.chat.id)
        if lock is None:
            lock = asyncio.Lock()
            self._chat_locks[message.chat.id] = lock
        async with lock:
            try:
                if query is not None:
                    await self._dispatch_callback(query)
                else:
                    await self._dispatch(message, update.update_id)
            except Exception:
                logger.exception("telegram.update.failed", extra={"update_id": update.update_id})
                await self._safe_reply(message.chat.id, ERROR_TEXT)

    async def _dispatch(self, message: TelegramMessage, update_id: int) -> None:
        if is_import_message(message):
            async with self._session_factory() as session:
                tenant_id = await self._linked_tenant(session, message)
            if tenant_id is not None:
                await self._catalog_import.handle_file(message, tenant_id)
            return
        text = (message.text or "").strip()
        if not text:
            await self.reply(message.chat.id, TEXT_ONLY_TEXT)
            return
        if text.startswith("/"):
            head, _, arg = text.partition(" ")
            command = head[1:].split("@", 1)[0].lower()
            handler = self._commands.get(command, self._cmd_help)
            await handler(message, arg.strip())
            return
        await self._handle_chat(message, update_id, text)

    async def _dispatch_callback(self, query: TelegramCallbackQuery) -> None:
        if not (query.data or "").startswith(f"{CALLBACK_PREFIX}:"):
            await self.client.answer_callback_query(query.id)
            return
        async with self._session_factory() as session:
            identity = await linking.get_identity(session, CHANNEL, str(query.from_user.id))
        if identity is None:
            await self.client.answer_callback_query(query.id)
            await self.reply(query.message.chat.id, NOT_LINKED_TEXT)
            return
        await self._catalog_import.handle_callback(query, identity.tenant_id)

    # ── Free-text business requests ──────────────────────────────────────────

    async def _handle_chat(self, message: TelegramMessage, update_id: int, text: str) -> None:
        chat_id = message.chat.id
        user_id = str(message.from_user.id)

        async with self._session_factory() as session:
            identity = await linking.get_identity(session, CHANNEL, user_id)
            if identity is None:
                await self.reply(chat_id, NOT_LINKED_TEXT)
                return
            tenant_id = identity.tenant_id

            try:
                await self.client.send_chat_action(chat_id, "typing")
            except TelegramAPIError:
                pass  # cosmetic only

            conversation_id = conversation_id_for(tenant_id, chat_id)
            history = await load_recent_history(session, tenant_id, conversation_id)
            normalized = NormalizedMessage.from_telegram(text, user_id, update_id, history)
            context = RequestContext(
                business_id=tenant_id,
                conversation_id=conversation_id,
                channel=CHANNEL,
                idempotency_key=normalized.idempotency_key,
            )
            result = await self._orchestrator.process(normalized, context, session)
            if result.success:
                await session.commit()
            else:
                await session.rollback()

        logger.info(
            "telegram.chat.processed",
            extra={"run_id": str(result.run_id), "intent": result.intent, "success": result.success},
        )
        await self.reply(chat_id, result.response_text)
        if result.success and result.pdf_url:
            await self._send_pdf(chat_id, tenant_id, result.pdf_url, result.document_number)

    # ── Commands (deterministic, never reach the LLM) ────────────────────────

    async def _cmd_start(self, message: TelegramMessage, arg: str) -> None:
        if arg:
            await self._cmd_link(message, arg)
            return
        async with self._session_factory() as session:
            identity = await linking.get_identity(session, CHANNEL, str(message.from_user.id))
            if identity is None:
                await self.reply(message.chat.id, f"Welcome to Munim!\n\n{NOT_LINKED_TEXT}")
                return
            business = await self._business_name(session, identity.tenant_id)
        await self.reply(message.chat.id, f"Welcome back! This chat is linked to **{business}**.\n\n{HELP_TEXT}")

    async def _cmd_link(self, message: TelegramMessage, arg: str) -> None:
        if not arg:
            await self.reply(message.chat.id, "Send your code like this: `/link YOUR-CODE`")
            return
        async with self._session_factory() as session:
            identity = await linking.redeem_link_code(
                session,
                arg,
                channel=CHANNEL,
                external_user_id=str(message.from_user.id),
                external_chat_id=str(message.chat.id),
                display_name=message.from_user.display_name,
            )
            if identity is None:
                await session.rollback()
                await self.reply(message.chat.id, LINK_FAILED_TEXT)
                return
            business = await self._business_name(session, identity.tenant_id)
            await session.commit()
        logger.info("telegram.chat.linked", extra={"tenant_id": str(identity.tenant_id)})
        await self.reply(message.chat.id, f"✅ Linked to **{business}**.\n\n{HELP_TEXT}")

    async def _cmd_unlink(self, message: TelegramMessage, arg: str) -> None:
        async with self._session_factory() as session:
            removed = await linking.unlink(session, CHANNEL, str(message.from_user.id))
            await session.commit()
        await self.reply(message.chat.id, "This chat is now disconnected." if removed else NOT_LINKED_TEXT)

    async def _cmd_help(self, message: TelegramMessage, arg: str) -> None:
        await self.reply(message.chat.id, HELP_TEXT)

    async def _cmd_quotations(self, message: TelegramMessage, arg: str) -> None:
        await self._list_documents(message, "quotation")

    async def _cmd_invoices(self, message: TelegramMessage, arg: str) -> None:
        await self._list_documents(message, "invoice")

    async def _cmd_pdf(self, message: TelegramMessage, arg: str) -> None:
        if not arg:
            await self.reply(message.chat.id, "Send the document number like this: `/pdf Q-202611-001`")
            return
        async with self._session_factory() as session:
            tenant_id = await self._linked_tenant(session, message)
            if tenant_id is None:
                return
            doc = await find_document_by_number(session, tenant_id, arg.split()[0])
        if doc is None:
            await self.reply(message.chat.id, f"I couldn't find a quotation or invoice numbered **{arg.split()[0].upper()}**.")
            return
        if not await self._send_pdf(message.chat.id, tenant_id, doc.pdf_url, doc.number):
            await self.reply(message.chat.id, f"The PDF for **{doc.number}** isn't available right now.")

    async def _cmd_cancel(self, message: TelegramMessage, arg: str) -> None:
        async with self._session_factory() as session:
            tenant_id = await self._linked_tenant(session, message)
            if tenant_id is None:
                return
            await conversation_store.clear(conversation_id_for(tenant_id, message.chat.id), session)
            await session.commit()
        await self.reply(message.chat.id, "Okay, I've discarded the request in progress.")

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _list_documents(self, message: TelegramMessage, document_type: str) -> None:
        async with self._session_factory() as session:
            tenant_id = await self._linked_tenant(session, message)
            if tenant_id is None:
                return
            docs = await list_recent_documents(session, tenant_id, document_type)
        label = _DOC_LABELS[document_type]
        if not docs:
            await self.reply(message.chat.id, f"You don't have any {label} yet.")
            return
        lines = [f"Your {len(docs)} most recent {label}:"] + [_format_document_line(d) for d in docs]
        lines.append(f"\nSend `/pdf {docs[0].number}` to get a PDF.")
        await self.reply(message.chat.id, "\n".join(lines))

    async def _linked_tenant(self, session: AsyncSession, message: TelegramMessage) -> Optional[uuid.UUID]:
        identity = await linking.get_identity(session, CHANNEL, str(message.from_user.id))
        if identity is None:
            await self.reply(message.chat.id, NOT_LINKED_TEXT)
            return None
        return identity.tenant_id

    @staticmethod
    async def _business_name(session: AsyncSession, tenant_id: uuid.UUID) -> str:
        name = (await session.execute(select(Tenant.business_name).where(Tenant.id == tenant_id))).scalar_one_or_none()
        return name or "your business"

    async def _send_pdf(self, chat_id: int, tenant_id: uuid.UUID, pdf_url: Optional[str], number: Optional[str]) -> bool:
        async with self._session_factory() as session:
            content = await load_pdf(session, pdf_url, tenant_id)
        if content is None:
            logger.warning("telegram.pdf.missing", extra={"document_number": number})
            return False
        await self.client.send_document(chat_id, content, filename=f"{number or 'document'}.pdf", caption=number)
        return True

    async def reply(
        self, chat_id: int, text: str, *, reply_markup: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send agent Markdown as Telegram HTML, falling back to plain text if Telegram rejects the markup.
        Buttons attach to the last chunk; returns that sent message.
        """
        chunks = split_message(text)
        sent: Optional[Dict[str, Any]] = None
        for index, chunk in enumerate(chunks):
            markup = reply_markup if index == len(chunks) - 1 else None
            try:
                sent = await self.client.send_message(chat_id, to_telegram_html(chunk), parse_mode="HTML",
                                                      reply_markup=markup)
            except TelegramAPIError as exc:
                if exc.error_code != 400:
                    raise
                sent = await self.client.send_message(chat_id, to_plain_text(chunk), reply_markup=markup)
        return sent

    async def _safe_reply(self, chat_id: int, text: str) -> None:
        try:
            await self.reply(chat_id, text)
        except Exception:
            logger.exception("telegram.reply.failed")
