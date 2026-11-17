"""
Tests for the web app read API (business, dashboard, customers, items, documents).

Runs against an isolated temporary SQLite database via a get_db_session
override, so figures are exact and the shared dev DB is untouched.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models
from app.api.v1.chat import get_db_session
from app.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.payment import Payment
from app.models.quotation import Quotation
from app.models.stock import Stock
from app.models.tenant import Tenant

TENANT_ID = uuid.UUID(get_settings().effective_sprint_tenant_id)
OTHER_TENANT_ID = uuid.UUID("c0ffee00-aaaa-4bbb-8ccc-dddddddddddd")


@pytest_asyncio.fixture
async def api(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'mgmt.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as s:
        s.add_all([
            Tenant(id=TENANT_ID, business_name="Vaidya Industrial Supplies", state="Maharashtra", gstin="27AAA"),
            Tenant(id=OTHER_TENANT_ID, business_name="Other Co", state="Gujarat"),
        ])
        await s.flush()
        ramesh = Customer(tenant_id=TENANT_ID, name="Ramesh Traders", state="Maharashtra")
        idle = Customer(tenant_id=TENANT_ID, name="Idle Buyer")
        stranger = Customer(tenant_id=OTHER_TENANT_ID, name="Not Mine")
        rod = Item(tenant_id=TENANT_ID, name="TMT Rod", gst_rate_percent=Decimal("18"),
                   unit_price=Decimal("68.50"), unit="kg", hsn_code="7214")
        bolt = Item(tenant_id=TENANT_ID, name="Hex Bolt", gst_rate_percent=Decimal("18"),
                    unit_price=Decimal("4.25"), unit="pcs")
        s.add_all([ramesh, idle, stranger, rod, bolt])
        await s.flush()
        s.add_all([
            Stock(item_id=rod.id, tenant_id=TENANT_ID, quantity_available=Decimal("500")),
            Stock(item_id=bolt.id, tenant_id=TENANT_ID, quantity_available=Decimal("4")),
            Quotation(tenant_id=TENANT_ID, customer_id=ramesh.id, quotation_number="Q-1",
                      status="draft", subtotal=Decimal("100")),
            Quotation(tenant_id=TENANT_ID, customer_id=ramesh.id, quotation_number="Q-2",
                      status="converted", subtotal=Decimal("50")),
            Quotation(tenant_id=OTHER_TENANT_ID, customer_id=stranger.id, quotation_number="Q-X",
                      status="draft", subtotal=Decimal("999")),
        ])
        paid = Invoice(tenant_id=TENANT_ID, customer_id=ramesh.id, invoice_number="INV-1",
                       status="paid", total_amount=Decimal("200"))
        partial = Invoice(tenant_id=TENANT_ID, customer_id=ramesh.id, invoice_number="INV-2",
                          status="partially_paid", total_amount=Decimal("300"))
        s.add_all([paid, partial])
        await s.flush()
        s.add_all([
            Payment(invoice_id=paid.id, amount=Decimal("200"), method="upi"),
            Payment(invoice_id=partial.id, amount=Decimal("120"), method="cash"),
        ])
        await s.commit()

    async def override_session():
        async with factory() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


async def test_business_profile(api):
    body = (await api.get("/api/v1/business")).json()
    assert body["business_name"] == "Vaidya Industrial Supplies"
    assert body["gstin"] == "27AAA"


async def test_dashboard_figures_are_computed_from_records(api):
    body = (await api.get("/api/v1/dashboard/summary")).json()
    assert body["total_sales"] == 500.0
    assert body["amount_received"] == 320.0
    assert body["outstanding_amount"] == 180.0  # INV-2: 300 billed − 120 paid
    assert body["unpaid_invoices"] == 1
    assert body["open_quotations"] == 1  # converted and other-tenant quotations excluded
    assert body["open_quotations_value"] == 100.0
    assert body["total_customers"] == 2
    assert [i["name"] for i in body["low_stock_items"]] == ["Hex Bolt"]
    assert {d["document_number"] for d in body["recent_documents"]} == {"Q-1", "Q-2", "INV-1", "INV-2"}


async def test_customers_include_activity_and_are_tenant_scoped(api):
    customers = {c["name"]: c for c in (await api.get("/api/v1/customers")).json()}
    assert set(customers) == {"Idle Buyer", "Ramesh Traders"}
    assert customers["Ramesh Traders"]["quotation_count"] == 2
    assert customers["Ramesh Traders"]["invoice_count"] == 2
    assert customers["Ramesh Traders"]["total_billed"] == 500.0
    assert customers["Idle Buyer"]["invoice_count"] == 0


async def test_items_include_stock(api):
    items = {i["name"]: i for i in (await api.get("/api/v1/items")).json()}
    assert items["TMT Rod"]["quantity_available"] == 500.0
    assert items["TMT Rod"]["low_stock"] is False
    assert items["Hex Bolt"]["low_stock"] is True
    assert items["TMT Rod"]["unit_price"] == 68.5


async def test_documents_list_is_tenant_scoped(api):
    numbers = {d["document_number"] for d in (await api.get("/api/v1/documents")).json()["documents"]}
    assert numbers == {"Q-1", "Q-2", "INV-1", "INV-2"}
