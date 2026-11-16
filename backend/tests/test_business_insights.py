"""Tests for deterministic, tenant-isolated business chat insights."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models
from app.db.base import Base
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.payment import Payment
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.orchestrator.context import RequestContext
from app.services.business_insights import low_stock_items, outstanding_dues, sales_summary, top_customers
from app.services.intent_classifier import classify_with_rules
from app.tools.read.sales_summary import SalesSummaryTool

TENANT_A = uuid.UUID("00000000-0000-0000-0000-000000000001")
TENANT_B = uuid.UUID("00000000-0000-0000-0000-000000000002")
NOW = datetime(2026, 11, 18, 10, tzinfo=timezone(timedelta(hours=5, minutes=30)))


@pytest_asyncio.fixture
async def session():
    # Batched inserts on SQLite read a row number back where the UUID primary
    # key belongs ('int' object has no attribute 'replace'); insert row by row.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", use_insertmanyvalues=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        db.add_all([
            Tenant(id=TENANT_A, business_name="A Traders", state="Maharashtra"),
            Tenant(id=TENANT_B, business_name="B Traders", state="Gujarat"),
        ])
        acme = Customer(id=uuid.uuid4(), tenant_id=TENANT_A, name="Acme", state="Maharashtra")
        bravo = Customer(id=uuid.uuid4(), tenant_id=TENANT_A, name="Bravo", state="Maharashtra")
        other = Customer(id=uuid.uuid4(), tenant_id=TENANT_B, name="Other", state="Gujarat")
        db.add_all([acme, bravo, other])
        await db.flush()
        invoices = [
            Invoice(id=uuid.uuid4(), tenant_id=TENANT_A, customer_id=acme.id, invoice_number="INV-A-1", subtotal=Decimal("100"), total_amount=Decimal("100"), created_at=datetime(2026, 11, 17, tzinfo=timezone.utc)),
            Invoice(id=uuid.uuid4(), tenant_id=TENANT_A, customer_id=acme.id, invoice_number="INV-A-2", subtotal=Decimal("200"), total_amount=Decimal("200"), created_at=datetime(2026, 11, 16, tzinfo=timezone.utc)),
            Invoice(id=uuid.uuid4(), tenant_id=TENANT_A, customer_id=bravo.id, invoice_number="INV-A-3", subtotal=Decimal("400"), total_amount=Decimal("400"), created_at=datetime(2026, 11, 3, tzinfo=timezone.utc)),
            Invoice(id=uuid.uuid4(), tenant_id=TENANT_B, customer_id=other.id, invoice_number="INV-B-1", subtotal=Decimal("999"), total_amount=Decimal("999"), created_at=datetime(2026, 11, 17, tzinfo=timezone.utc)),
        ]
        db.add_all(invoices)
        await db.flush()
        db.add(Payment(id=uuid.uuid4(), invoice_id=invoices[0].id, amount=Decimal("25"), method="upi"))
        item = Item(id=uuid.uuid4(), tenant_id=TENANT_A, name="Low Bolt", hsn_code="7318", gst_rate_percent=Decimal("18"), unit_price=Decimal("10"), unit="pcs")
        healthy = Item(id=uuid.uuid4(), tenant_id=TENANT_A, name="Healthy Nut", hsn_code="7318", gst_rate_percent=Decimal("18"), unit_price=Decimal("10"), unit="pcs")
        hidden = Item(id=uuid.uuid4(), tenant_id=TENANT_B, name="Hidden Item", hsn_code="7318", gst_rate_percent=Decimal("18"), unit_price=Decimal("10"), unit="pcs")
        db.add_all([item, healthy, hidden])
        await db.flush()
        db.add_all([
            Stock(item_id=item.id, tenant_id=TENANT_A, quantity_available=Decimal("5")),
            Stock(item_id=healthy.id, tenant_id=TENANT_A, quantity_available=Decimal("50")),
            Stock(item_id=hidden.id, tenant_id=TENANT_B, quantity_available=Decimal("1")),
        ])
        await db.commit()
        yield db
    await engine.dispose()


async def test_business_insights_are_correct_for_periods_and_isolated_by_tenant(session):
    sales = await sales_summary(session, TENANT_A, "this_week", now=NOW)
    assert sales.total == Decimal("300") and sales.invoice_count == 2
    assert await sales_summary(session, TENANT_B, "this_week", now=NOW) == type(sales)(Decimal("999"), 1)

    dues = await outstanding_dues(session, TENANT_A)
    assert [(due.customer_name, due.amount) for due in dues] == [("Bravo", Decimal("400")), ("Acme", Decimal("275"))]

    stock = await low_stock_items(session, TENANT_A)
    assert [(item.name, item.quantity) for item in stock] == [("Low Bolt", Decimal("5"))]

    customers = await top_customers(session, TENANT_A, "this_month", now=NOW)
    assert [(customer.name, customer.total) for customer in customers] == [("Bravo", Decimal("400")), ("Acme", Decimal("300"))]


async def test_empty_business_returns_zeroes_and_no_rows(session):
    empty = uuid.UUID("00000000-0000-0000-0000-000000000003")
    session.add(Tenant(id=empty, business_name="Empty", state="Delhi"))
    await session.commit()
    assert await sales_summary(session, empty, "today", now=NOW) == type(await sales_summary(session, empty, "today", now=NOW))(Decimal("0"), 0)
    assert await outstanding_dues(session, empty) == []
    assert await low_stock_items(session, empty) == []
    assert await top_customers(session, empty, "this_month", now=NOW) == []


async def test_chat_rule_and_tool_return_deterministic_sales(session):
    result = classify_with_rules("What were my sales this week?")
    assert (result.intent, result.business_query_type, result.business_period) == ("business_query", "sales", "this_week")
    context = RequestContext(business_id=TENANT_A, conversation_id=uuid.uuid4(), channel="web")
    response = await SalesSummaryTool().execute(SalesSummaryTool.input_schema(period="this_week"), context, session)
    assert response.data["response_text"].startswith("**Sales this week:** ₹")
