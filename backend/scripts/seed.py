"""
M1M Sprint 1 — Idempotent Seed Script
=======================================

⚠️  TEST / DEVELOPMENT DATA ONLY — NOT REAL BUSINESS INFORMATION ⚠️
All names, phone numbers, GSTINs, and addresses below are fictional.
Do NOT use this data in production.

Seeds exactly:
  - 1 fictional test tenant  (Vaidya Industrial Supplies, Pune)
  - 8 fictional customers    (Maharashtra intra-state + inter-state mix)
  - 12 fictional catalog items (industrial/hardware, mixed GST rates)
  - 12 opening stock records  (one per item)

Idempotency guarantee:
  - All records use deterministic UUID5 identifiers derived from a fixed namespace.
  - INSERT ... ON CONFLICT DO NOTHING ensures no duplicates on re-runs.
  - Running this script N times produces exactly the same DB state.

Usage:
  python backend/scripts/seed.py
  (Run from the workspace root — m1m/)

Prerequisites:
  1. .env present at workspace root with DATABASE_URL set.
  2. alembic upgrade head has been run successfully.
"""

from __future__ import annotations

import asyncio
import ssl
import sys
import uuid
from decimal import Decimal
from pathlib import Path

# ─── sys.path setup ──────────────────────────────────────────────────────────
# seed.py is at backend/scripts/seed.py → backend/ is one level up
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

# ─── Load .env from workspace root (m1m/.env) ────────────────────────────────
_workspace_dir = _backend_dir.parent
_env_file = _workspace_dir / ".env"
if not _env_file.exists():
    _env_file = _backend_dir / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_env_file), override=False)
    except ImportError:
        pass  # rely on env vars already exported in the shell

# ─── App imports (after path + env setup) ────────────────────────────────────
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.config import get_settings  # noqa: E402
import app.models  # noqa: F401, E402 — register all ORM models with Base.metadata
from app.models.tenant import Tenant  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.item import Item  # noqa: E402
from app.models.stock import Stock  # noqa: E402

# ─── Deterministic UUID namespace ────────────────────────────────────────────
# All Sprint 1 seed records are derived from this fixed namespace via UUID5.
# Changing this namespace would change all seed UUIDs — do NOT change it.
SEED_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c9")


def seed_uuid(key: str) -> uuid.UUID:
    """Generate a deterministic UUID5 for a Sprint 1 seed record."""
    return uuid.uuid5(SEED_NAMESPACE, f"sprint1:{key}")


# ─── Sprint 1 tenant ─────────────────────────────────────────────────────────
# TEST DATA — fictional business. State code 27 = Maharashtra.
TENANT_DATA = {
    "business_name": "Vaidya Industrial Supplies",
    # Fictional GSTIN: 27 (Maharashtra) + AABCV1234A (fictional PAN) + 1Z5
    "gstin": "27AABCV1234A1Z5",
    "state": "Maharashtra",
    "address": (
        "Plot No. 45, MIDC Industrial Area, "
        "Pimpri-Chinchwad, Pune - 411018, Maharashtra"
    ),
    "logo_url": None,
}

# ─── Customers (8 total) ─────────────────────────────────────────────────────
# 4 Maharashtra (intra-state) + 4 inter-state
# TEST DATA — fictional names and phone numbers

CUSTOMERS: list[dict] = [
    # ── Maharashtra — intra-state (CGST + SGST will apply) ────────────────
    {
        "id": seed_uuid("customer:ramesh-traders-pune"),
        "name": "Ramesh Traders",
        "phone": "+919900000001",
        "gstin": "27AABCR1001A1Z3",
        "state": "Maharashtra",
        "address": "Shop No. 12, Bhawani Peth Market, Pune - 411042",
    },
    {
        "id": seed_uuid("customer:ganesh-engineering-nashik"),
        "name": "Ganesh Engineering Works",
        "phone": "+919900000002",
        "gstin": "27AABCG2002A1Z1",
        "state": "Maharashtra",
        "address": "Satpur MIDC, Nashik - 422007",
    },
    {
        "id": seed_uuid("customer:mahalaxmi-hardware-aurangabad"),
        "name": "Shri Mahalaxmi Hardware",
        "phone": "+919900000003",
        "gstin": None,  # Unregistered / B2C customer
        "state": "Maharashtra",
        "address": "Cidco N-6, Aurangabad - 431003",
    },
    {
        "id": seed_uuid("customer:patel-constructions-mumbai"),
        "name": "Patel Constructions",
        "phone": "+919900000004",
        "gstin": "27AABCP4004A1Z7",
        "state": "Maharashtra",
        "address": "Andheri East, Mumbai - 400069",
    },
    # ── Inter-state (IGST will apply) ─────────────────────────────────────
    {
        "id": seed_uuid("customer:gujarat-steel-ahmedabad"),
        "name": "Gujarat Steel Suppliers",
        "phone": "+919900000005",
        "gstin": "24AABCG5005A1Z2",  # 24 = Gujarat
        "state": "Gujarat",
        "address": "GIDC Naroda, Ahmedabad - 382330",
    },
    {
        "id": seed_uuid("customer:shriram-industries-bangalore"),
        "name": "Shri Ram Industries",
        "phone": "+919900000006",
        "gstin": "29AABCS6006A1Z9",  # 29 = Karnataka
        "state": "Karnataka",
        "address": "Peenya Industrial Area, Bengaluru - 560058",
    },
    {
        "id": seed_uuid("customer:hyderabad-metal-works"),
        "name": "Hyderabad Metal Works",
        "phone": "+919900000007",
        "gstin": "36AABCH7007A1Z5",  # 36 = Telangana
        "state": "Telangana",
        "address": "IDA Nacharam, Hyderabad - 500076",
    },
    {
        "id": seed_uuid("customer:delhi-industrial-corp"),
        "name": "Delhi Industrial Corporation",
        "phone": "+919900000008",
        "gstin": "07AABCD8008A1Z8",  # 07 = Delhi
        "state": "Delhi",
        "address": "Okhla Industrial Estate Phase III, New Delhi - 110020",
    },
]

# ─── Item catalog (12 items) ──────────────────────────────────────────────────
# Realistic industrial/hardware items — TEST DATA
# GST rate mix: 5% · 12% · 18% · 28%

ITEMS: list[dict] = [
    # ── 18% GST — Steel products (HSN 72xx) ──────────────────────────────
    {
        "id": seed_uuid("item:tmt-steel-rod-12mm"),
        "name": "TMT Steel Rod 12mm",
        "hsn_code": "7213",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("58.00"),
        "unit": "kg",
    },
    {
        "id": seed_uuid("item:ms-steel-plate-6mm"),
        "name": "MS Steel Plate 6mm",
        "hsn_code": "7208",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("72.00"),
        "unit": "kg",
    },
    # ── 18% GST — Fasteners (HSN 7318) ───────────────────────────────────
    {
        "id": seed_uuid("item:ms-hex-bolt-m12x50"),
        "name": "MS Hex Bolt M12x50mm",
        "hsn_code": "7318",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("8.00"),
        "unit": "pcs",
    },
    {
        "id": seed_uuid("item:ms-hex-nut-m12"),
        "name": "MS Hex Nut M12",
        "hsn_code": "7318",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("5.00"),
        "unit": "pcs",
    },
    {
        "id": seed_uuid("item:ms-flat-washer-m12"),
        "name": "MS Flat Washer M12",
        "hsn_code": "7318",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("3.00"),
        "unit": "pcs",
    },
    # ── 18% GST — Pipes & Electrical ─────────────────────────────────────
    {
        "id": seed_uuid("item:pvc-conduit-pipe-25mm"),
        "name": "PVC Rigid Conduit Pipe 25mm",
        "hsn_code": "3917",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("85.00"),
        "unit": "mtr",
    },
    {
        "id": seed_uuid("item:electrical-wire-2-5sqmm"),
        "name": "Electrical Wire 2.5sqmm Single Core",
        "hsn_code": "8544",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("28.00"),
        "unit": "mtr",
    },
    # ── 18% GST — Welding consumables ────────────────────────────────────
    {
        "id": seed_uuid("item:welding-electrode-e6013-5kg"),
        "name": "Welding Electrode E6013 5kg Box",
        "hsn_code": "8311",
        "gst_rate_percent": Decimal("18.00"),
        "unit_price": Decimal("320.00"),
        "unit": "box",
    },
    # ── 5% GST — Personal protective equipment ────────────────────────────
    {
        "id": seed_uuid("item:safety-helmet-is2925"),
        "name": "Safety Helmet IS:2925",
        "hsn_code": "6506",
        "gst_rate_percent": Decimal("5.00"),
        "unit_price": Decimal("350.00"),
        "unit": "pcs",
    },
    # ── 12% GST — Bearings & abrasives ───────────────────────────────────
    {
        "id": seed_uuid("item:ball-bearing-6205"),
        "name": "Deep Groove Ball Bearing 6205",
        "hsn_code": "8482",
        "gst_rate_percent": Decimal("12.00"),
        "unit_price": Decimal("145.00"),
        "unit": "pcs",
    },
    {
        "id": seed_uuid("item:cutting-disc-4inch"),
        "name": "Angle Grinder Cutting Disc 4 Inch",
        "hsn_code": "6804",
        "gst_rate_percent": Decimal("12.00"),
        "unit_price": Decimal("28.00"),
        "unit": "pcs",
    },
    # ── 28% GST — Heavy lifting equipment ────────────────────────────────
    {
        "id": seed_uuid("item:chain-pulley-block-1ton"),
        "name": "GI Chain Pulley Block 1 Ton",
        "hsn_code": "8425",
        "gst_rate_percent": Decimal("28.00"),
        "unit_price": Decimal("2850.00"),
        "unit": "pcs",
    },
]

# ─── Opening stock (one row per item, same order) ────────────────────────────
# Realistic quantities for an industrial supplier — TEST DATA

STOCK: list[dict] = [
    {"item_id": seed_uuid("item:tmt-steel-rod-12mm"),         "quantity_available": Decimal("2500.00")},
    {"item_id": seed_uuid("item:ms-steel-plate-6mm"),          "quantity_available": Decimal("850.00")},
    {"item_id": seed_uuid("item:ms-hex-bolt-m12x50"),          "quantity_available": Decimal("5000.00")},
    {"item_id": seed_uuid("item:ms-hex-nut-m12"),              "quantity_available": Decimal("8000.00")},
    {"item_id": seed_uuid("item:ms-flat-washer-m12"),          "quantity_available": Decimal("10000.00")},
    {"item_id": seed_uuid("item:pvc-conduit-pipe-25mm"),       "quantity_available": Decimal("1200.00")},
    {"item_id": seed_uuid("item:electrical-wire-2-5sqmm"),     "quantity_available": Decimal("3000.00")},
    {"item_id": seed_uuid("item:welding-electrode-e6013-5kg"), "quantity_available": Decimal("200.00")},
    {"item_id": seed_uuid("item:safety-helmet-is2925"),        "quantity_available": Decimal("150.00")},
    {"item_id": seed_uuid("item:ball-bearing-6205"),           "quantity_available": Decimal("500.00")},
    {"item_id": seed_uuid("item:cutting-disc-4inch"),          "quantity_available": Decimal("2000.00")},
    {"item_id": seed_uuid("item:chain-pulley-block-1ton"),     "quantity_available": Decimal("25.00")},
]

# Quick sanity check: ITEMS and STOCK must have equal length
assert len(ITEMS) == 12, f"Expected 12 items, got {len(ITEMS)}"
assert len(STOCK) == 12, f"Expected 12 stock rows, got {len(STOCK)}"
assert len(ITEMS) == len(STOCK), "Item count ≠ stock row count"


# ─── Main seed function ───────────────────────────────────────────────────────

async def seed() -> None:
    settings = get_settings()
    tenant_id = uuid.UUID(settings.effective_sprint_tenant_id)

    # Supabase uses SSL with a self-signed cert chain — disable verification
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        connect_args={"ssl": _ssl_ctx},
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    tenant_created = tenant_existing = 0
    customers_created = customers_existing = 0
    items_created = items_existing = 0
    stock_created = stock_existing = 0

    async with session_factory() as session:
        async with session.begin():

            # ── Tenant ──────────────────────────────────────────────────────
            stmt = pg_insert(Tenant).values(id=tenant_id, **TENANT_DATA)
            stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
            result = await session.execute(stmt)
            if result.rowcount == 0:
                tenant_existing += 1
            else:
                tenant_created += 1

            # ── Customers ───────────────────────────────────────────────────
            for c in CUSTOMERS:
                stmt = pg_insert(Customer).values(tenant_id=tenant_id, **c)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    customers_existing += 1
                else:
                    customers_created += 1

            # ── Items ────────────────────────────────────────────────────────
            for item in ITEMS:
                stmt = pg_insert(Item).values(tenant_id=tenant_id, **item)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    items_existing += 1
                else:
                    items_created += 1

            # ── Stock (one row per item, item_id is the PK) ──────────────────
            for s in STOCK:
                stmt = pg_insert(Stock).values(tenant_id=tenant_id, **s)
                stmt = stmt.on_conflict_do_nothing(index_elements=["item_id"])
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    stock_existing += 1
                else:
                    stock_created += 1

    await engine.dispose()

    # ── Print seed report ────────────────────────────────────────────────────
    w = 44
    print()
    print("=" * w)
    print("  M1M SPRINT 1 DATABASE SEED")
    print("=" * w)
    print()
    print("Tenant:")
    print(f"  Business : {TENANT_DATA['business_name']}")
    print(f"  Tenant ID: {tenant_id}")
    print(f"  State    : {TENANT_DATA['state']}")
    print(f"  GSTIN    : {TENANT_DATA['gstin']}")
    print(f"  Created  : {tenant_created}    Existing: {tenant_existing}")
    print()
    print("Customers:")
    print(f"  Created  : {customers_created}    Existing: {customers_existing}")
    print()
    print("Items:")
    print(f"  Created  : {items_created}   Existing: {items_existing}")
    print()
    print("Stock:")
    print(f"  Created  : {stock_created}   Existing: {stock_existing}")
    print()
    print("=" * w)
    print()

    if tenant_existing or customers_existing or items_existing or stock_existing:
        print("  [INFO] Existing records were detected and skipped.")
        print("  [OK]   No duplicates were created (seed is idempotent).")
    else:
        print("  [OK]   Fresh seed complete.")
    print()


if __name__ == "__main__":
    asyncio.run(seed())
