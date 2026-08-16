"""
M1M Sprint 1 Step 1 — Database Seed Integration Tests
=======================================================

These are integration tests against the live Supabase database.

Prerequisites (must be true before running):
  1. `alembic upgrade head` has completed successfully.
  2. `python backend/scripts/seed.py` has been run at least once.
  3. The DATABASE_URL in .env points to the same database.

Run from backend/ directory:
  pytest tests/ -v

Tests verify:
  ✓ Exactly 1 Sprint 1 tenant
  ✓ Tenant UUID is deterministic
  ✓ Exactly 8 customers
  ✓ Exactly 12 items
  ✓ Exactly 12 stock records
  ✓ Every stock row matches an item
  ✓ Maharashtra customers exist (intra-state)
  ✓ Non-Maharashtra customers exist (inter-state)
  ✓ Items have HSN codes
  ✓ Items have positive GST rates
  ✓ Items have positive unit prices
  ✓ At least 3 distinct GST rate brackets
  ✓ Stock quantities > 0
  ✓ Seed is idempotent (no duplicates after multiple runs)
"""

import uuid

import pytest
from sqlalchemy import func, select, distinct

from app.config import SPRINT_TENANT_ID_DEFAULT
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.item import Item
from app.models.stock import Stock


# ─── Test constants ──────────────────────────────────────────────────────────

SEED_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c9")


def seed_uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"sprint1:{key}")


# The documented Sprint 1 dev tenant UUID
EXPECTED_TENANT_ID = uuid.UUID(SPRINT_TENANT_ID_DEFAULT)

EXPECTED_CUSTOMERS = 8
EXPECTED_ITEMS = 12
EXPECTED_STOCK = 12


# ─── Tenant tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sprint_tenant_exists(db_session):
    """Exactly one Sprint 1 tenant must be present."""
    result = await db_session.execute(
        select(func.count()).select_from(Tenant).where(
            Tenant.id == EXPECTED_TENANT_ID
        )
    )
    count = result.scalar_one()
    assert count == 1, f"Expected 1 Sprint 1 tenant, got {count}"


@pytest.mark.asyncio
async def test_tenant_id_is_deterministic(db_session):
    """
    The tenant UUID must be the documented dev UUID.
    Running the seed script a second time must produce the same UUID.
    """
    from app.config import get_settings
    settings = get_settings()
    actual_tid = uuid.UUID(settings.effective_sprint_tenant_id)
    assert actual_tid == EXPECTED_TENANT_ID, (
        f"Tenant ID mismatch.\n"
        f"  Expected: {EXPECTED_TENANT_ID}\n"
        f"  Got:      {actual_tid}"
    )


@pytest.mark.asyncio
async def test_tenant_business_details(db_session):
    """Tenant must have correct business name, state, and a GSTIN."""
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == EXPECTED_TENANT_ID)
    )
    tenant = result.scalar_one()
    assert tenant.business_name == "Vaidya Industrial Supplies"
    assert tenant.state == "Maharashtra"
    assert tenant.gstin is not None and len(tenant.gstin) > 0


# ─── Customer tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_count(db_session):
    """Exactly 8 customers must exist for the Sprint 1 tenant."""
    result = await db_session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.tenant_id == EXPECTED_TENANT_ID
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_CUSTOMERS, (
        f"Expected {EXPECTED_CUSTOMERS} customers, got {count}"
    )


@pytest.mark.asyncio
async def test_all_customers_belong_to_sprint_tenant(db_session):
    """Every seeded customer must have tenant_id == EXPECTED_TENANT_ID."""
    result = await db_session.execute(
        select(Customer).where(Customer.tenant_id == EXPECTED_TENANT_ID)
    )
    customers = result.scalars().all()
    assert len(customers) == EXPECTED_CUSTOMERS
    for c in customers:
        assert c.tenant_id == EXPECTED_TENANT_ID, (
            f"Customer {c.name!r} has wrong tenant_id: {c.tenant_id}"
        )


@pytest.mark.asyncio
async def test_maharashtra_customers_exist(db_session):
    """At least one intra-state (Maharashtra) customer must exist."""
    result = await db_session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.tenant_id == EXPECTED_TENANT_ID,
            Customer.state == "Maharashtra",
        )
    )
    count = result.scalar_one()
    assert count >= 1, "No Maharashtra (intra-state) customers found"


@pytest.mark.asyncio
async def test_inter_state_customers_exist(db_session):
    """At least one inter-state customer must exist (for IGST coverage)."""
    result = await db_session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.tenant_id == EXPECTED_TENANT_ID,
            Customer.state != "Maharashtra",
        )
    )
    count = result.scalar_one()
    assert count >= 1, "No inter-state customers found"


@pytest.mark.asyncio
async def test_customer_state_variety(db_session):
    """Customers must span at least 2 distinct states."""
    result = await db_session.execute(
        select(distinct(Customer.state)).where(
            Customer.tenant_id == EXPECTED_TENANT_ID
        )
    )
    states = {row[0] for row in result.all()}
    assert len(states) >= 2, f"Expected ≥2 distinct customer states, got: {states}"


# ─── Item tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_item_count(db_session):
    """Exactly 12 items must exist for the Sprint 1 tenant."""
    result = await db_session.execute(
        select(func.count()).select_from(Item).where(
            Item.tenant_id == EXPECTED_TENANT_ID
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_ITEMS, f"Expected {EXPECTED_ITEMS} items, got {count}"


@pytest.mark.asyncio
async def test_all_items_have_hsn_codes(db_session):
    """Every item must have a non-null HSN code."""
    result = await db_session.execute(
        select(func.count()).select_from(Item).where(
            Item.tenant_id == EXPECTED_TENANT_ID,
            Item.hsn_code.is_(None),
        )
    )
    null_count = result.scalar_one()
    assert null_count == 0, f"{null_count} items are missing HSN codes"


@pytest.mark.asyncio
async def test_all_items_have_positive_gst_rates(db_session):
    """Every item must have a GST rate > 0."""
    result = await db_session.execute(
        select(func.count()).select_from(Item).where(
            Item.tenant_id == EXPECTED_TENANT_ID,
            Item.gst_rate_percent > 0,
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_ITEMS, (
        f"Expected {EXPECTED_ITEMS} items with GST rate > 0, got {count}"
    )


@pytest.mark.asyncio
async def test_all_items_have_positive_unit_prices(db_session):
    """Every item must have a unit_price > 0."""
    result = await db_session.execute(
        select(func.count()).select_from(Item).where(
            Item.tenant_id == EXPECTED_TENANT_ID,
            Item.unit_price > 0,
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_ITEMS, (
        f"Expected {EXPECTED_ITEMS} items with positive prices, got {count}"
    )


@pytest.mark.asyncio
async def test_gst_rate_variety(db_session):
    """Items must span at least 3 distinct GST rate brackets (5/12/18/28%)."""
    result = await db_session.execute(
        select(distinct(Item.gst_rate_percent)).where(
            Item.tenant_id == EXPECTED_TENANT_ID
        )
    )
    rates = {row[0] for row in result.all()}
    assert len(rates) >= 3, (
        f"Expected ≥3 distinct GST rates for coverage of intra/inter-state edge "
        f"cases, found only: {sorted(rates)}"
    )


# ─── Stock tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_count(db_session):
    """Exactly 12 stock records must exist for the Sprint 1 tenant."""
    result = await db_session.execute(
        select(func.count()).select_from(Stock).where(
            Stock.tenant_id == EXPECTED_TENANT_ID
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_STOCK, f"Expected {EXPECTED_STOCK} stock rows, got {count}"


@pytest.mark.asyncio
async def test_every_item_has_exactly_one_stock_row(db_session):
    """
    The set of item_ids in the stock table must exactly equal
    the set of item ids in the item table for this tenant.
    """
    items_result = await db_session.execute(
        select(Item.id).where(Item.tenant_id == EXPECTED_TENANT_ID)
    )
    item_ids = {row[0] for row in items_result.all()}

    stock_result = await db_session.execute(
        select(Stock.item_id).where(Stock.tenant_id == EXPECTED_TENANT_ID)
    )
    stock_item_ids = {row[0] for row in stock_result.all()}

    missing_stock = item_ids - stock_item_ids
    orphan_stock = stock_item_ids - item_ids

    assert not missing_stock, f"Items without stock rows: {missing_stock}"
    assert not orphan_stock, f"Stock rows without matching items: {orphan_stock}"
    assert item_ids == stock_item_ids


@pytest.mark.asyncio
async def test_all_stock_belong_to_sprint_tenant(db_session):
    """Every stock record must belong to the Sprint 1 tenant."""
    result = await db_session.execute(
        select(func.count()).select_from(Stock).where(
            Stock.tenant_id == EXPECTED_TENANT_ID
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_STOCK


@pytest.mark.asyncio
async def test_opening_stock_quantities_are_positive(db_session):
    """All opening stock quantities must be > 0."""
    result = await db_session.execute(
        select(func.count()).select_from(Stock).where(
            Stock.tenant_id == EXPECTED_TENANT_ID,
            Stock.quantity_available > 0,
        )
    )
    count = result.scalar_one()
    assert count == EXPECTED_STOCK, (
        f"Expected {EXPECTED_STOCK} positive-quantity stock rows, got {count}"
    )


# ─── Idempotency test ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_idempotency(db_session):
    """
    After the seed script has been run (even multiple times),
    record counts must be exactly 1 / 8 / 12 / 12.
    Verifies no duplicates were created by subsequent runs.
    """
    tenant_count = (await db_session.execute(
        select(func.count()).select_from(Tenant).where(
            Tenant.id == EXPECTED_TENANT_ID
        )
    )).scalar_one()

    customer_count = (await db_session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.tenant_id == EXPECTED_TENANT_ID
        )
    )).scalar_one()

    item_count = (await db_session.execute(
        select(func.count()).select_from(Item).where(
            Item.tenant_id == EXPECTED_TENANT_ID
        )
    )).scalar_one()

    stock_count = (await db_session.execute(
        select(func.count()).select_from(Stock).where(
            Stock.tenant_id == EXPECTED_TENANT_ID
        )
    )).scalar_one()

    assert tenant_count == 1, (
        f"Duplicate tenant detected: {tenant_count} rows "
        f"(seed is NOT idempotent for tenant)"
    )
    assert customer_count == EXPECTED_CUSTOMERS, (
        f"Customer count wrong: expected {EXPECTED_CUSTOMERS}, got {customer_count} "
        f"(possible duplicate if > {EXPECTED_CUSTOMERS})"
    )
    assert item_count == EXPECTED_ITEMS, (
        f"Item count wrong: expected {EXPECTED_ITEMS}, got {item_count}"
    )
    assert stock_count == EXPECTED_STOCK, (
        f"Stock count wrong: expected {EXPECTED_STOCK}, got {stock_count}"
    )
