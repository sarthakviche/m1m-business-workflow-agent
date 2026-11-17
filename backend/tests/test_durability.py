"""
What must hold once real businesses depend on the platform: documents can't be
half-made or numbered twice, PDFs survive restarts, stock can't be oversold, and
one business can't use up everyone's AI allowance.

The concurrency tests need real row locks, so they only run on Postgres
(TEST_DATABASE_URL, as in CI). SQLite has a single writer and would prove nothing.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.api.v1.documents import _DOCS_ROOT
from app.config import get_settings
from app.main import app as fastapi_app
from app.models.ai_usage import AiUsage
from app.models.customer import Customer
from app.models.document import DocumentFile
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.quotation import Quotation
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.rate_limit import RateLimitMiddleware
from app.services import ai_quota, pdf_service
from app.services.ai_quota import reserve_ai_call
from app.services.doc_number import generate_invoice_number, generate_quotation_number
from app.services.invoice_service import (
    InsufficientStockError,
    QuotationNotFoundError,
    convert_quotation_to_invoice,
    create_direct_invoice,
)
from app.services.quotation_service import create_quotation
from tests.test_multi_tenant import bearer, client, session_factory, sign_up  # noqa: F401 — pytest fixtures

needs_postgres = pytest.mark.skipif(
    get_settings().async_database_url.startswith("sqlite"),
    reason="Needs real row locks: set TEST_DATABASE_URL",
)

_CSV = "Item,Rate,GST %,HSN,UOM,Stock\nSteel Rod 12mm,68.50,18,7214,kg,500\n".encode()


async def _business(session_factory, stock="100"):  # noqa: F811
    """A business with one customer and one stocked item."""
    async with session_factory() as s:
        tenant = Tenant(business_name=f"Co {uuid.uuid4().hex[:6]}", state="Maharashtra")
        s.add(tenant)
        await s.flush()
        customer = Customer(tenant_id=tenant.id, name="Asha Stores", state="Maharashtra")
        item = Item(tenant_id=tenant.id, name="Steel Rod 12mm", gst_rate_percent=Decimal("18"),
                    unit_price=Decimal("100"), unit="kg", hsn_code="7214")
        s.add_all([customer, item])
        await s.flush()
        s.add(Stock(item_id=item.id, tenant_id=tenant.id, quantity_available=Decimal(stock)))
        await s.commit()
        return tenant.id, customer.id, item.id


async def _load(session, customer_id, item_id):
    return await session.get(Customer, customer_id), await session.get(Item, item_id)


async def _count(session_factory, model, tenant_id):  # noqa: F811
    async with session_factory() as s:
        return (await s.execute(select(func.count()).select_from(model).where(model.tenant_id == tenant_id))).scalar_one()


# ── Document numbering ───────────────────────────────────────────────────────


async def test_numbers_are_consecutive_and_separate_per_business(session_factory):  # noqa: F811
    a, _, _ = await _business(session_factory)
    b, _, _ = await _business(session_factory)
    month = datetime(2026, 11, 1)
    async with session_factory() as s:
        assert await generate_invoice_number(s, a, month) == "INV-202611-001"
        assert await generate_invoice_number(s, a, month) == "INV-202611-002"
        assert await generate_invoice_number(s, b, month) == "INV-202611-001"
        assert await generate_quotation_number(s, a, month) == "Q-202611-001"
        assert await generate_invoice_number(s, a, datetime(2026, 12, 1)) == "INV-202612-001"
        await s.commit()


async def test_numbering_continues_after_documents_from_before_the_counter(session_factory):  # noqa: F811
    tenant, customer, _ = await _business(session_factory)
    async with session_factory() as s:
        s.add(Invoice(tenant_id=tenant, customer_id=customer, invoice_number="INV-202611-007",
                      status="unpaid", total_amount=Decimal("1")))
        await s.flush()
        assert await generate_invoice_number(s, tenant, datetime(2026, 11, 1)) == "INV-202611-008"
        await s.commit()


async def test_a_rolled_back_document_gives_its_number_back(session_factory):  # noqa: F811
    tenant, _, _ = await _business(session_factory)
    month = datetime(2026, 11, 1)
    async with session_factory() as s:
        assert await generate_invoice_number(s, tenant, month) == "INV-202611-001"
        await s.rollback()
    async with session_factory() as s:
        assert await generate_invoice_number(s, tenant, month) == "INV-202611-001"


# ── PDFs are durable and all-or-nothing ──────────────────────────────────────


async def test_pdf_lives_in_the_database_not_on_disk(session_factory):  # noqa: F811
    tenant, customer_id, item_id = await _business(session_factory)
    async with session_factory() as s:
        customer, item = await _load(s, customer_id, item_id)
        data = await create_quotation(session=s, tenant_id=tenant, customer=customer, items_with_qty=[(item, Decimal("2"))])
        await s.commit()

    assert not (_DOCS_ROOT / str(tenant)).exists()  # survives the free host wiping its disk
    async with session_factory() as s:
        assert (await pdf_service.load_pdf(s, data["pdf_url"], tenant)).startswith(b"%PDF")
        assert await pdf_service.load_pdf(s, data["pdf_url"], uuid.uuid4()) is None


@pytest.mark.parametrize("url_suffix", ["../x.pdf", "a/b/c.pdf", "quotations/none.pdf", "quotations/x.txt"])
async def test_load_pdf_rejects_bad_paths(session_factory, url_suffix):  # noqa: F811
    tenant, _, _ = await _business(session_factory)
    async with session_factory() as s:
        assert await pdf_service.load_pdf(s, f"/documents/{tenant}/{url_suffix}", tenant) is None


async def test_failed_pdf_undoes_the_whole_invoice(client, session_factory, monkeypatch):  # noqa: F811
    """A crash after the stock decrement must leave no invoice, no stock change and no used number."""
    tenant_id = uuid.UUID(await sign_up(client, "owner", "Owner Co"))
    auth = bearer("owner")
    await client.post("/api/v1/catalog/import", headers=auth, json={"items": [
        {"name": "Steel Rod 12mm", "unit_price": "100", "unit": "kg", "gst_rate_percent": "18", "quantity_available": "50"},
    ]})

    def broken(*_args):
        raise pdf_service.DocumentRenderError("renderer down")

    monkeypatch.setattr(pdf_service, "_render_pdf", broken)
    failed = await client.post("/api/v1/chat", headers=auth, json={
        "message": "create invoice for Ramesh Traders for 10 units Steel Rod 12mm",
    })
    body = failed.json()
    assert body["success"] is False and body["document_number"] is None

    assert await _count(session_factory, Invoice, tenant_id) == 0
    assert await _count(session_factory, DocumentFile, tenant_id) == 0
    items = (await client.get("/api/v1/items", headers=auth)).json()
    assert items[0]["quantity_available"] == 50.0


async def test_invoice_number_is_reused_after_a_failure(session_factory, monkeypatch):  # noqa: F811
    tenant, customer_id, item_id = await _business(session_factory)
    async with session_factory() as s:
        customer, item = await _load(s, customer_id, item_id)

        def broken(*_args):
            raise pdf_service.DocumentRenderError("renderer down")

        with monkeypatch.context() as patch:
            patch.setattr(pdf_service, "_render_pdf", broken)
            with pytest.raises(pdf_service.DocumentRenderError):
                await create_direct_invoice(session=s, tenant_id=tenant, customer=customer, items_with_qty=[(item, Decimal("1"))])
        await s.rollback()

    async with session_factory() as s:
        customer, item = await _load(s, customer_id, item_id)
        data = await create_direct_invoice(session=s, tenant_id=tenant, customer=customer, items_with_qty=[(item, Decimal("1"))])
        await s.commit()
    assert data["invoice_number"].endswith("-001")


# ── AI quotas ────────────────────────────────────────────────────────────────


@pytest.fixture
def small_quota(monkeypatch):
    settings = get_settings().model_copy(update={"ai_daily_limit_per_business": 2, "ai_daily_limit_total": 3})
    monkeypatch.setattr(ai_quota, "get_settings", lambda: settings)


async def test_each_business_has_its_own_allowance(session_factory, small_quota):  # noqa: F811
    async with session_factory() as s:
        await s.execute(AiUsage.__table__.delete())
        await s.commit()
    a, _, _ = await _business(session_factory)
    b, _, _ = await _business(session_factory)
    async with session_factory() as s:
        assert await reserve_ai_call(s, a) is True
        assert await reserve_ai_call(s, a) is True
        assert await reserve_ai_call(s, a) is False  # A has used its share...
        assert await reserve_ai_call(s, b) is True   # ...and B isn't affected.
        assert await reserve_ai_call(s, b) is False  # The overall ceiling protects the shared key.


async def test_over_quota_assistant_still_works_by_rules(client, monkeypatch):  # noqa: F811
    await sign_up(client, "owner", "Owner Co")
    auth = bearer("owner")
    await client.post("/api/v1/catalog/import", headers=auth, json={"items": [
        {"name": "Steel Rod 12mm", "unit_price": "100", "unit": "kg", "gst_rate_percent": "18"},
    ]})

    async def no_quota(_session, _tenant):
        return False

    from app.agent import graph
    monkeypatch.setattr(graph, "reserve_ai_call", no_quota)

    def must_not_call_ai(*_args):
        pytest.fail("Gemini was called over quota")

    monkeypatch.setattr(graph, "classify_intent_sync", must_not_call_ai)

    done = await client.post("/api/v1/chat", headers=auth, json={
        "message": "create quotation for Ramesh Traders for 10 units Steel Rod 12mm",
    })
    assert done.json()["document_number"]

    unclear = await client.post("/api/v1/chat", headers=auth, json={"message": "create a quotation"})
    assert "today's limit" in unclear.json()["response_text"]


async def test_over_quota_photo_upload_is_refused_but_csv_works(client, monkeypatch):  # noqa: F811
    await sign_up(client, "owner", "Owner Co")
    auth = bearer("owner")

    async def no_quota(_session, _tenant):
        return False

    from app.services import catalog_import
    monkeypatch.setattr(catalog_import, "reserve_ai_call", no_quota)

    photo = await client.post("/api/v1/catalog/import/preview", headers=auth,
                              files={"file": ("list.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")})
    assert photo.status_code == 429
    assert "CSV" in photo.json()["message"]

    sheet = await client.post("/api/v1/catalog/import/preview", headers=auth,
                              files={"file": ("list.csv", _CSV, "text/csv")})
    assert sheet.status_code == 200
    assert sheet.json()["rows"][0]["name"] == "Steel Rod 12mm"


# ── Rate limits ──────────────────────────────────────────────────────────────


def _limited_client(limit=2, now=None):
    async def ok(_request):
        return PlainTextResponse("ok")

    inner = Starlette(routes=[Route("/api/thing", ok, methods=["GET", "POST", "OPTIONS"]), Route("/free", ok)])
    clock = now or (lambda: 0.0)
    limited = RateLimitMiddleware(inner, rules=(("POST", "/api/thing", limit), (None, "/api/", 100)), clock=clock)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=limited, client=("1.2.3.4", 1)), base_url="http://test")


async def test_rate_limit_blocks_then_recovers():
    moment = [0.0]
    async with _limited_client(now=lambda: moment[0]) as http:
        assert (await http.post("/api/thing")).status_code == 200
        assert (await http.post("/api/thing")).status_code == 200
        blocked = await http.post("/api/thing")
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "rate_limit"
        assert int(blocked.headers["Retry-After"]) > 0

        moment[0] = 61.0
        assert (await http.post("/api/thing")).status_code == 200


async def test_rate_limit_only_touches_matching_routes():
    async with _limited_client(limit=1) as http:
        await http.post("/api/thing")
        assert (await http.post("/api/thing")).status_code == 429
        assert (await http.get("/api/thing")).status_code == 200  # the general, higher limit
        assert (await http.options("/api/thing")).status_code == 200  # never block CORS preflight
        assert (await http.get("/free")).status_code == 200


def test_telegram_webhook_is_exempt_from_ip_limits():
    middleware = RateLimitMiddleware(None)
    assert middleware._rule_for("POST", "/api/v1/telegram/webhook")[1] is None
    assert middleware._rule_for("POST", "/api/v1/chat")[1] == 60


def test_rate_limit_is_installed_on_the_app():
    assert any(m.cls is RateLimitMiddleware for m in fastapi_app.user_middleware)


# ── Real concurrency (Postgres only) ─────────────────────────────────────────


@pytest_asyncio.fixture
async def pg_sessions():
    engine = create_async_engine(get_settings().async_database_url, pool_size=25)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@needs_postgres
async def test_simultaneous_first_documents_never_collide(pg_sessions):
    """The bug this replaces: with no rows yet to lock, two requests both took -001."""
    tenant, _, _ = await _business(pg_sessions)

    async def one():
        async with pg_sessions() as s:
            number = await generate_invoice_number(s, tenant, datetime(2026, 11, 1))
            await s.commit()
            return number

    numbers = await asyncio.gather(*(one() for _ in range(20)))
    assert sorted(numbers) == [f"INV-202611-{i:03d}" for i in range(1, 21)]


@needs_postgres
async def test_simultaneous_invoices_cannot_oversell(pg_sessions):
    tenant, customer_id, item_id = await _business(pg_sessions, stock="30")

    async def one():
        async with pg_sessions() as s:
            customer, item = await _load(s, customer_id, item_id)
            await s.get(Stock, item_id)  # an earlier read in this session must not hide newer stock
            try:
                data = await create_direct_invoice(session=s, tenant_id=tenant, customer=customer,
                                                   items_with_qty=[(item, Decimal("10"))])
                await s.commit()
                return data["invoice_number"]
            except InsufficientStockError:
                await s.rollback()
                return None

    results = await asyncio.gather(*(one() for _ in range(8)))
    issued = [r for r in results if r]
    assert len(issued) == 3 and len(set(issued)) == 3
    async with pg_sessions() as s:
        assert (await s.get(Stock, item_id)).quantity_available == Decimal("0")
    assert await _count(pg_sessions, Invoice, tenant) == 3


@needs_postgres
async def test_a_quotation_converts_only_once(pg_sessions):
    tenant, customer_id, item_id = await _business(pg_sessions)
    async with pg_sessions() as s:
        customer, item = await _load(s, customer_id, item_id)
        number = (await create_quotation(session=s, tenant_id=tenant, customer=customer,
                                         items_with_qty=[(item, Decimal("5"))]))["quotation_number"]
        await s.commit()

    async def one():
        async with pg_sessions() as s:
            try:
                await convert_quotation_to_invoice(s, tenant, number)
                await s.commit()
                return True
            except QuotationNotFoundError:
                await s.rollback()
                return False

    assert sorted(await asyncio.gather(*(one() for _ in range(6)))) == [False] * 5 + [True]
    assert await _count(pg_sessions, Invoice, tenant) == 1
    async with pg_sessions() as s:
        assert (await s.get(Stock, item_id)).quantity_available == Decimal("95")
    assert await _count(pg_sessions, Quotation, tenant) == 1


@needs_postgres
async def test_every_table_has_row_level_security(pg_sessions):
    """Without this, the publishable key in the web app could read the table through Supabase's API."""
    async with pg_sessions() as s:
        exposed = (await s.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity"
        ))).scalars().all()
    assert exposed == []
