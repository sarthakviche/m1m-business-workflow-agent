"""
Tests for the Telegram channel adapter.

Every test runs against its own temporary SQLite database (schema from the ORM
models) with a fake Telegram client, so nothing touches the shared dev DB or
the real Bot API. Gemini is disabled so the agent's deterministic regex path
is exercised and results are reproducible.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models
from app.api.v1.chat import get_db_session
from app.channels import linking
from app.channels.telegram import router as telegram_router
from app.channels.telegram.client import TelegramAPIError, TelegramClient
from app.channels.telegram.formatting import split_message, to_plain_text, to_telegram_html
from app.channels.telegram.handler import NOT_LINKED_TEXT, TelegramUpdateHandler, conversation_id_for
from app.channels.telegram.types import TelegramUpdate
from app.config import get_settings
from app.conversation.history import load_recent_history
from app.conversation.state import ConversationState, merge_line_items
from app.conversation.store import ConversationStore
from app.db.base import Base
from app.main import app as fastapi_app
from app.models.channel import ChannelIdentity
from app.models.conversation_log import ConversationLog
from app.models.customer import Customer
from app.models.item import Item
from app.models.quotation import Quotation, QuotationLine
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.orchestrator.orchestrator import OrchestratorResult
from app.services import intent_classifier, pdf_service

TENANT_ID = uuid.UUID(get_settings().effective_sprint_tenant_id)
OTHER_TENANT_ID = uuid.UUID("b1c2d3e4-f5a6-4b7c-8d9e-0fa1b2c3d4e5")
ROD_PRICE = Decimal("68.50")
USER_ID = 424242

_update_ids = itertools.count(10_000)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def session_factory(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'telegram.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        session.add_all([
            Tenant(id=TENANT_ID, business_name="Vaidya Industrial Supplies", state="Maharashtra"),
            Tenant(id=OTHER_TENANT_ID, business_name="Other Co", state="Gujarat"),
        ])
        await session.flush()
        rod = Item(tenant_id=TENANT_ID, name="TMT Steel Rod 12mm", hsn_code="7214",
                   gst_rate_percent=Decimal("18"), unit_price=ROD_PRICE, unit="kg")
        bolt = Item(tenant_id=TENANT_ID, name="MS Hex Bolt M10", hsn_code="7318",
                    gst_rate_percent=Decimal("18"), unit_price=Decimal("4.25"), unit="pcs")
        session.add_all([rod, bolt, Customer(tenant_id=TENANT_ID, name="Ramesh Traders")])
        await session.flush()
        session.add_all([
            Stock(item_id=rod.id, tenant_id=TENANT_ID, quantity_available=Decimal("500")),
            Stock(item_id=bolt.id, tenant_id=TENANT_ID, quantity_available=Decimal("1000")),
        ])
        await session.commit()

    # Generated PDFs go to the temp dir; Gemini is off so extraction is deterministic.
    monkeypatch.setattr(pdf_service, "_DOCS_DIR", tmp_path / "docs")
    (tmp_path / "docs").mkdir()

    def _no_gemini():
        raise RuntimeError("Gemini disabled in tests")

    monkeypatch.setattr(intent_classifier, "get_gemini_client", _no_gemini)

    yield factory
    await engine.dispose()


class FakeTelegramClient:
    def __init__(self, reject_html: bool = False, files: Dict[str, bytes] | None = None):
        self.reject_html = reject_html
        self.messages: List[Dict[str, Any]] = []
        self.documents: List[Dict[str, Any]] = []
        self.files = files or {}
        self.downloads: List[str] = []
        self.answered: List[str] = []
        self.keyboards_removed: List[int] = []

    async def send_message(self, chat_id, text, *, parse_mode=None, reply_markup=None):
        if self.reject_html and parse_mode:
            raise TelegramAPIError("sendMessage", "Bad Request: can't parse entities", 400)
        sent = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup is not None:
            sent["reply_markup"] = reply_markup
        self.messages.append(sent)
        return {"message_id": len(self.messages)}

    async def answer_callback_query(self, callback_query_id, text=None):
        self.answered.append(callback_query_id)

    async def remove_inline_keyboard(self, chat_id, message_id):
        self.keyboards_removed.append(message_id)

    async def download_file(self, file_id, *, max_bytes):
        self.downloads.append(file_id)
        return self.files[file_id]

    async def send_document(self, chat_id, content, *, filename=None, caption=None):
        self.documents.append({"chat_id": chat_id, "content": content, "filename": filename, "caption": caption})

    async def send_chat_action(self, chat_id, action="typing"):
        pass

    @property
    def last_text(self) -> str:
        return self.messages[-1]["text"]


class SpyOrchestrator:
    """Records calls; optionally writes to the session to test commit/rollback."""

    def __init__(self, result: OrchestratorResult | None = None, write_customer: str | None = None):
        self.calls: List[tuple] = []
        self.result = result or OrchestratorResult(response_text="ok", run_id=uuid.uuid4())
        self.write_customer = write_customer

    async def process(self, message, context, session):
        self.calls.append((message, context))
        if self.write_customer:
            session.add(Customer(tenant_id=context.business_id, name=self.write_customer))
            await session.flush()
        return self.result


def make_update(text: str, *, user_id: int = USER_ID, chat_type: str = "private", update_id: int | None = None) -> TelegramUpdate:
    return TelegramUpdate.model_validate({
        "update_id": update_id if update_id is not None else next(_update_ids),
        "message": {
            "message_id": 1,
            "date": 1_700_000_000,
            "chat": {"id": user_id, "type": chat_type},
            "from": {"id": user_id, "is_bot": False, "first_name": "Sarthak"},
            "text": text,
        },
    })


async def link_user(factory, tenant_id: uuid.UUID = TENANT_ID, user_id: int = USER_ID) -> None:
    async with factory() as session:
        session.add(ChannelIdentity(tenant_id=tenant_id, channel="telegram",
                                    external_user_id=str(user_id), external_chat_id=str(user_id)))
        await session.commit()


async def count(factory, model) -> int:
    async with factory() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


# ─── Formatting ──────────────────────────────────────────────────────────────

def test_to_telegram_html_escapes_then_formats():
    html = to_telegram_html("Quotation **Q-1** for <A & B> _draft_ item_code `X`")
    assert "<b>Q-1</b>" in html
    assert "&lt;A &amp; B&gt;" in html
    assert "<i>draft</i>" in html
    assert "item_code" in html
    assert "<code>X</code>" in html


def test_to_plain_text_strips_markers():
    assert to_plain_text("**Q-1** _draft_ `x`") == "Q-1 draft x"


def test_split_message_keeps_lines_intact_and_under_limit():
    text = "\n".join(f"• line {i} **bold**" for i in range(600))
    chunks = split_message(text, limit=1000)
    assert len(chunks) > 1
    assert all(len(to_telegram_html(c)) <= 1000 for c in chunks)
    assert "\n".join(chunks).count("**bold**") == 600


# ─── Bot API client ──────────────────────────────────────────────────────────

async def test_client_posts_payload_and_returns_result():
    seen = {}

    def transport(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})

    client = TelegramClient("123:SECRET", http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)))
    result = await client.send_message(5, "<b>hi</b>", parse_mode="HTML")
    assert result == {"message_id": 7}
    assert seen["path"] == "/bot123:SECRET/sendMessage"
    assert b'"parse_mode":"HTML"' in seen["body"].replace(b" ", b"")
    await client.aclose()


async def test_client_errors_never_expose_token():
    def api_error(request):
        return httpx.Response(401, json={"ok": False, "error_code": 401, "description": "Unauthorized"})

    def network_error(request):
        raise httpx.ConnectError("boom", request=request)

    for transport, code in ((api_error, 401), (network_error, None)):
        client = TelegramClient("123:SECRET", http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)))
        with pytest.raises(TelegramAPIError) as exc_info:
            await client.get_me()
        assert "SECRET" not in str(exc_info.value)
        assert exc_info.value.error_code == code
        await client.aclose()


# ─── Linking ─────────────────────────────────────────────────────────────────

async def test_link_code_is_single_use_and_normalized(session_factory):
    async with session_factory() as session:
        issued = await linking.create_link_code(session, TENANT_ID, "telegram", timedelta(minutes=5))
        await session.commit()

    messy = f" {issued.code[:4].lower()}-{issued.code[4:].lower()} "
    async with session_factory() as session:
        identity = await linking.redeem_link_code(session, messy, channel="telegram",
                                                  external_user_id="1", external_chat_id="1", display_name="A")
        await session.commit()
    assert identity is not None and identity.tenant_id == TENANT_ID

    async with session_factory() as session:
        again = await linking.redeem_link_code(session, issued.code, channel="telegram",
                                               external_user_id="2", external_chat_id="2", display_name="B")
    assert again is None


async def test_link_code_rejects_expired_wrong_channel_and_garbage(session_factory):
    async with session_factory() as session:
        expired = await linking.create_link_code(session, TENANT_ID, "telegram", timedelta(minutes=-1))
        whatsapp = await linking.create_link_code(session, TENANT_ID, "whatsapp", timedelta(minutes=5))
        await session.commit()

    async with session_factory() as session:
        for code in (expired.code, whatsapp.code, "NOPE", ""):
            assert await linking.redeem_link_code(session, code, channel="telegram", external_user_id="1",
                                                  external_chat_id="1", display_name=None) is None


async def test_link_code_stores_only_hash(session_factory):
    from app.models.channel import ChannelLinkCode

    async with session_factory() as session:
        issued = await linking.create_link_code(session, TENANT_ID, "telegram", timedelta(minutes=5))
        await session.commit()
        stored = (await session.execute(select(ChannelLinkCode))).scalar_one()
    assert issued.code not in stored.code_hash


# ─── Handler: access control, dedup, transactions ────────────────────────────

async def test_unlinked_chat_never_reaches_orchestrator(session_factory):
    client, spy = FakeTelegramClient(), SpyOrchestrator()
    handler = TelegramUpdateHandler(client, session_factory, orchestrator=spy)

    await handler.handle(make_update("create quotation for Ramesh Traders 10 TMT Steel Rod 12mm"))

    assert spy.calls == []
    assert client.last_text == to_telegram_html(NOT_LINKED_TEXT)


async def test_group_chats_and_bots_are_ignored(session_factory):
    await link_user(session_factory)
    client, spy = FakeTelegramClient(), SpyOrchestrator()
    handler = TelegramUpdateHandler(client, session_factory, orchestrator=spy)

    await handler.handle(make_update("hello", chat_type="group"))
    bot_update = make_update("hello")
    bot_update.message.from_user.is_bot = True
    await handler.handle(bot_update)

    assert spy.calls == [] and client.messages == []


async def test_redelivered_update_is_processed_once(session_factory):
    await link_user(session_factory)
    client, spy = FakeTelegramClient(), SpyOrchestrator()
    handler = TelegramUpdateHandler(client, session_factory, orchestrator=spy)

    update = make_update("price of bolts")
    await handler.handle(update)
    await handler.handle(update)

    assert len(spy.calls) == 1
    assert len(client.messages) == 1


async def test_context_comes_from_identity_and_history_from_db(session_factory):
    await link_user(session_factory)
    conversation_id = conversation_id_for(TENANT_ID, USER_ID)
    turn_time = datetime.now(timezone.utc)
    async with session_factory() as session:
        session.add_all([
            ConversationLog(tenant_id=TENANT_ID, conversation_id=conversation_id, channel="telegram",
                            direction="inbound", raw_message="quote for Ramesh Traders", created_at=turn_time),
            ConversationLog(tenant_id=TENANT_ID, conversation_id=conversation_id, channel="telegram",
                            direction="outbound", raw_message="Which items?", created_at=turn_time),
        ])
        await session.commit()

    client, spy = FakeTelegramClient(), SpyOrchestrator()
    await TelegramUpdateHandler(client, session_factory, orchestrator=spy).handle(make_update("10 rods"))

    message, context = spy.calls[0]
    assert context.business_id == TENANT_ID
    assert context.channel == "telegram"
    assert context.conversation_id == conversation_id
    assert message.conversation_history == [
        {"role": "user", "content": "quote for Ramesh Traders"},
        {"role": "assistant", "content": "Which items?"},
    ]


async def test_failed_result_rolls_back_writes(session_factory):
    await link_user(session_factory)
    before = await count(session_factory, Customer)
    spy = SpyOrchestrator(
        result=OrchestratorResult(response_text="nope", success=False, error_code="validation_error"),
        write_customer="Should Not Persist",
    )
    client = FakeTelegramClient()
    await TelegramUpdateHandler(client, session_factory, orchestrator=spy).handle(make_update("x"))

    assert await count(session_factory, Customer) == before
    assert client.last_text == "nope"


async def test_rejected_html_falls_back_to_plain_text(session_factory):
    await link_user(session_factory)
    client = FakeTelegramClient(reject_html=True)
    spy = SpyOrchestrator(result=OrchestratorResult(response_text="**Q-1** created", run_id=uuid.uuid4()))
    await TelegramUpdateHandler(client, session_factory, orchestrator=spy).handle(make_update("x"))

    assert client.messages == [{"chat_id": USER_ID, "text": "Q-1 created", "parse_mode": None}]


# ─── End to end through the real agent (regex extraction, no LLM) ───────────

async def _real_handler(factory) -> tuple[TelegramUpdateHandler, FakeTelegramClient]:
    client = FakeTelegramClient()
    return TelegramUpdateHandler(client, factory), client


async def test_link_then_create_quotation_with_exact_catalog_values(session_factory):
    handler, client = await _real_handler(session_factory)
    async with session_factory() as session:
        issued = await linking.create_link_code(session, TENANT_ID, "telegram", timedelta(minutes=5))
        await session.commit()

    await handler.handle(make_update(f"/start {issued.code}"))
    assert "Linked to <b>Vaidya Industrial Supplies</b>" in client.last_text

    await handler.handle(make_update("create quotation for Ramesh Traders for 10 TMT Steel Rod 12mm"))

    async with session_factory() as session:
        quotation = (await session.execute(select(Quotation))).scalar_one()
        lines = (await session.execute(select(QuotationLine))).scalars().all()
    assert len(lines) == 1
    assert lines[0].quantity == Decimal("10")
    assert lines[0].unit_price == ROD_PRICE
    assert quotation.subtotal == ROD_PRICE * 10

    reply = client.last_text
    assert f"<b>{quotation.quotation_number}</b>" in reply
    assert "Ramesh Traders" in reply and "TMT Steel Rod 12mm" in reply and "685.00" in reply
    async with session_factory() as session:
        stored_pdf = await pdf_service.load_pdf(session, quotation.pdf_url, TENANT_ID)
    assert stored_pdf.startswith(b"%PDF")
    assert client.documents == [{
        "chat_id": USER_ID,
        "content": stored_pdf,
        "filename": f"{quotation.quotation_number}.pdf",
        "caption": quotation.quotation_number,
    }]


async def test_unknown_item_creates_nothing(session_factory):
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)
    customers_before = await count(session_factory, Customer)

    await handler.handle(make_update("create quotation for Brand New Buyer for 50 unicorn horns"))

    assert "wasn't found in your catalog" in client.last_text
    assert await count(session_factory, Quotation) == 0
    assert await count(session_factory, Customer) == customers_before
    assert client.documents == []


async def test_multi_turn_quotation_does_not_duplicate_items(session_factory):
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)

    await handler.handle(make_update("create a quotation for Ramesh Traders"))
    assert "Which items and quantities" in client.last_text

    await handler.handle(make_update("10 TMT Steel Rod 12mm"))

    async with session_factory() as session:
        lines = (await session.execute(select(QuotationLine))).scalars().all()
    assert [(line.quantity, line.unit_price) for line in lines] == [(Decimal("10"), ROD_PRICE)]


async def test_quotations_and_pdf_commands_read_from_db(session_factory):
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)

    await handler.handle(make_update("/quotations"))
    assert client.last_text == "You don't have any quotations yet."

    await handler.handle(make_update("create quotation for Ramesh Traders for 4 MS Hex Bolt M10"))
    async with session_factory() as session:
        number = (await session.execute(select(Quotation.quotation_number))).scalar_one()

    await handler.handle(make_update("/quotations"))
    assert f"<b>{number}</b> — Ramesh Traders — ₹17.00 — draft" in client.last_text

    client.documents.clear()
    await handler.handle(make_update(f"/pdf {number.lower()}"))
    assert client.documents[0]["caption"] == number

    await handler.handle(make_update("/pdf Q-000000-999"))
    assert "couldn't find" in client.last_text


async def test_documents_are_tenant_scoped(session_factory):
    await link_user(session_factory)
    other_user = USER_ID + 1
    await link_user(session_factory, tenant_id=OTHER_TENANT_ID, user_id=other_user)
    handler, client = await _real_handler(session_factory)

    await handler.handle(make_update("create quotation for Ramesh Traders for 2 MS Hex Bolt M10"))
    async with session_factory() as session:
        number = (await session.execute(select(Quotation.quotation_number))).scalar_one()

    client.documents.clear()
    await handler.handle(make_update(f"/pdf {number}", user_id=other_user))
    assert client.documents == []
    assert "couldn't find" in client.last_text


async def test_cancel_discards_pending_request(session_factory):
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)

    await handler.handle(make_update("create a quotation for Ramesh Traders"))
    await handler.handle(make_update("/cancel"))

    store = ConversationStore()
    async with session_factory() as session:
        assert await store.get(conversation_id_for(TENANT_ID, USER_ID), TENANT_ID, session) is None


# ─── Conversation state, history, PDF paths ──────────────────────────────────

def test_merge_line_items_replaces_repeated_items():
    rods = {"item_name": "TMT Steel Rod 12mm", "quantity": 10}
    merged = merge_line_items([rods], [{"item_name": "tmt steel rod 12MM", "quantity": 12},
                                       {"item_name": "Cement", "quantity": 5}])
    assert merged == [{"item_name": "tmt steel rod 12MM", "quantity": 12}, {"item_name": "Cement", "quantity": 5}]


async def test_conversation_store_respects_tenant_and_ttl(session_factory):
    conv_id = uuid.uuid4()
    state = ConversationState(conversation_id=conv_id, business_id=TENANT_ID, pending_intent="quotation",
                              extracted_entities={"customer_name": "Ramesh Traders"})
    async with session_factory() as session:
        await ConversationStore().save(state, session)
        await session.commit()

        loaded = await ConversationStore().get(conv_id, TENANT_ID, session)
        assert loaded.pending_intent == "quotation"
        assert loaded.extracted_entities == {"customer_name": "Ramesh Traders"}
        assert await ConversationStore().get(conv_id, OTHER_TENANT_ID, session) is None
        assert await ConversationStore(ttl=timedelta(seconds=-1)).get(conv_id, TENANT_ID, session) is None


async def test_history_is_chronological_and_limited(session_factory):
    conv_id = uuid.uuid4()
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with session_factory() as session:
        for turn in range(3):
            for direction in ("outbound", "inbound"):  # insertion order must not matter
                session.add(ConversationLog(tenant_id=TENANT_ID, conversation_id=conv_id, channel="telegram",
                                            direction=direction, raw_message=f"{direction}-{turn}",
                                            created_at=base + timedelta(minutes=turn)))
        await session.commit()
        history = await load_recent_history(session, TENANT_ID, conv_id, limit=4)
    assert [h["content"] for h in history] == ["inbound-1", "outbound-1", "inbound-2", "outbound-2"]


async def test_history_ignores_turns_outside_the_window(session_factory):
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        for minutes_ago, text in ((80, "old"), (5, "recent")):
            session.add(ConversationLog(tenant_id=TENANT_ID, conversation_id=conv_id, channel="telegram",
                                        direction="inbound", raw_message=text,
                                        created_at=now - timedelta(minutes=minutes_ago)))
        await session.commit()
        history = await load_recent_history(session, TENANT_ID, conv_id)
    assert [h["content"] for h in history] == ["recent"]


def test_merge_keeps_known_quantity_when_item_repeated_without_one():
    merged = merge_line_items([{"item_name": "Bolt", "quantity": 50}], [{"item_name": "bolt", "quantity": None}])
    assert merged == [{"item_name": "Bolt", "quantity": 50}]


def test_regex_extraction_never_invents_quantities():
    from app.services.intent_classifier import _extract_via_regex

    res = _extract_via_regex("create quotation for Ramesh Traders for MS Hex Bolt M10")
    assert [li.quantity for li in res.line_items] == [None]

    context = "Assistant: Which items and quantities should be included for **Ramesh Traders**?"
    for message in ("TMT Steel Rod 12mm", "Ma hex bolt"):
        res = _extract_via_regex(message, context)
        assert [li.quantity for li in res.line_items] == [None], message


# ─── Regression: live Telegram session of 2 Nov 2026 ────────────────────────

async def _backdate_conversation(factory, minutes: int) -> None:
    async with factory() as session:
        for row in (await session.execute(select(ConversationLog))).scalars():
            row.created_at = row.created_at - timedelta(minutes=minutes)
        await session.commit()


async def test_missing_quantity_is_asked_never_assumed(session_factory):
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)

    await handler.handle(make_update("create quotation for Ramesh Traders for MS Hex Bolt M10"))
    assert "How many <b>MS Hex Bolt M10</b>" in client.last_text
    assert await count(session_factory, Quotation) == 0

    await handler.handle(make_update("50 pcs"))
    async with session_factory() as session:
        lines = (await session.execute(select(QuotationLine))).scalars().all()
    assert [(line.quantity, line.unit_price) for line in lines] == [(Decimal("50"), Decimal("4.25"))]


async def test_spec_numbers_are_not_read_as_quantities(session_factory):
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)

    await handler.handle(make_update("create a quotation for Ramesh Traders"))
    await handler.handle(make_update("TMT Steel Rod 12mm"))

    assert "How many <b>TMT Steel Rod 12mm</b>" in client.last_text
    assert await count(session_factory, Quotation) == 0


async def test_stale_request_is_not_resumed_hours_later(session_factory):
    """Replays the live session: an old unfinished request must not capture new messages."""
    await link_user(session_factory)
    handler, client = await _real_handler(session_factory)
    customers_before = await count(session_factory, Customer)

    await handler.handle(make_update("I want you to create a quotation for Sri Salasar Insulations"))
    assert "Sri Salasar Insulations" in client.last_text
    await handler.handle(make_update("Show me a list of all the items"))

    # 80 minutes pass before the next messages.
    await _backdate_conversation(session_factory, 80)

    await handler.handle(make_update("Hi"))
    assert "Sri Salasar" not in client.last_text

    await handler.handle(make_update("Ma hex bolt"))
    assert "Sri Salasar" not in client.last_text
    assert await count(session_factory, Quotation) == 0
    assert await count(session_factory, Customer) == customers_before


def test_resolve_pdf_path_rejects_other_tenants_and_traversal(session_factory, tmp_path):
    tenant_dir = tmp_path / "docs" / str(TENANT_ID) / "quotations"
    tenant_dir.mkdir(parents=True)
    (tenant_dir / "Q-1.pdf").write_bytes(b"%PDF-1.4")
    url = f"/documents/{TENANT_ID}/quotations/Q-1.pdf"

    assert pdf_service.resolve_pdf_path(url, TENANT_ID) == (tenant_dir / "Q-1.pdf").resolve()
    assert pdf_service.resolve_pdf_path(url, OTHER_TENANT_ID) is None
    assert pdf_service.resolve_pdf_path(f"/documents/{TENANT_ID}/../{OTHER_TENANT_ID}/x.pdf", TENANT_ID) is None
    assert pdf_service.resolve_pdf_path(None, TENANT_ID) is None


# ─── HTTP endpoints ──────────────────────────────────────────────────────────

class RecordingHandler:
    def __init__(self):
        self.updates: List[TelegramUpdate] = []

    async def handle(self, update):
        self.updates.append(update)


@pytest.fixture
def webhook_client(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_bot_token", "123:TEST")
    monkeypatch.setattr(settings, "telegram_webhook_secret", "s3cret")
    recorder = RecordingHandler()
    fastapi_app.dependency_overrides[telegram_router.get_telegram_handler] = lambda: recorder
    yield TestClient(fastapi_app), recorder
    fastapi_app.dependency_overrides.clear()


def test_webhook_requires_matching_secret(webhook_client):
    client, recorder = webhook_client
    payload = make_update("hi").model_dump(by_alias=True)

    assert client.post("/api/v1/telegram/webhook", json=payload).status_code == 401
    wrong = {"X-Telegram-Bot-Api-Secret-Token": "nope"}
    assert client.post("/api/v1/telegram/webhook", json=payload, headers=wrong).status_code == 401
    assert recorder.updates == []

    ok = client.post("/api/v1/telegram/webhook", json=payload,
                     headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"})
    assert ok.status_code == 200
    assert [u.update_id for u in recorder.updates] == [payload["update_id"]]


def test_webhook_acknowledges_unparseable_payloads(webhook_client):
    client, recorder = webhook_client
    response = client.post("/api/v1/telegram/webhook", json={"unexpected": True},
                           headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"})
    assert response.status_code == 200
    assert recorder.updates == []


def test_webhook_disabled_without_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", None)
    response = TestClient(fastapi_app).post("/api/v1/telegram/webhook", json={})
    assert response.status_code == 404


async def test_link_code_endpoint_issues_redeemable_code(session_factory):
    async def override_session():
        async with session_factory() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_db_session] = override_session
    try:
        transport = httpx.ASGITransport(app=fastapi_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            response = await http.post("/api/v1/telegram/link-codes")
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 201
    code = response.json()["code"]
    async with session_factory() as session:
        identity = await linking.redeem_link_code(session, code, channel="telegram", external_user_id="9",
                                                  external_chat_id="9", display_name=None)
    assert identity.tenant_id == TENANT_ID


def test_unknown_api_key_returns_401_not_500():
    response = TestClient(fastapi_app).post("/api/v1/chat", json={"message": "hi"},
                                            headers={"X-API-Key": "definitely-not-a-key"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_error"
