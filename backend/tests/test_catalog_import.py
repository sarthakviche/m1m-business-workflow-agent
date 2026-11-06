"""
Tests for price-list import (onboarding) and business profile updates.

Gemini is replaced by a stub returning a fixed extraction, so these tests
cover what the app does with model output: validation, matching against the
existing catalog, and the upsert. Runs against an isolated SQLite database.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models
from app.api.v1.chat import get_db_session
from app.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app
from app.models.item import Item
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.services import catalog_import
from app.services.catalog_import import (
    CatalogExtraction,
    ExtractedCatalogItem,
    build_preview,
    normalize_unit,
    parse_csv_catalog,
)

TENANT_ID = uuid.UUID(get_settings().effective_sprint_tenant_id)
OTHER_TENANT_ID = uuid.UUID("c0ffee00-aaaa-4bbb-8ccc-eeeeeeeeeeee")

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _item(name: str, price: str, gst: str = "18", tenant=TENANT_ID) -> Item:
    return Item(id=uuid.uuid4(), tenant_id=tenant, name=name, unit_price=Decimal(price),
                gst_rate_percent=Decimal(gst), unit="pcs")


# ── Row validation and matching (pure) ────────────────────────────────────────

def test_rows_with_bad_values_are_flagged_not_fixed():
    extraction = CatalogExtraction(items=[
        ExtractedCatalogItem(name="  Hex  Bolt M10 ", unit_price=4.5, unit="Nos.", gst_rate_percent=18, hsn_code="7318"),
        ExtractedCatalogItem(name="Washer", unit_price=None, unit="pcs", gst_rate_percent=17),
        ExtractedCatalogItem(name="Rod", unit_price=-2, unit=None, hsn_code="12", gst_rate_percent=None),
    ])
    rows = {r.name: r for r in build_preview(extraction, []).rows}

    bolt = rows["Hex Bolt M10"]
    assert (bolt.unit_price, bolt.unit, bolt.gst_rate_percent, bolt.hsn_code) == (Decimal("4.50"), "pcs", Decimal("18.00"), "7318")
    assert bolt.issues == [] and bolt.match == "new"

    washer = rows["Washer"]
    assert washer.unit_price is None and washer.gst_rate_percent is None
    assert "Price missing" in washer.issues
    assert any("not a GST slab" in i for i in washer.issues)

    rod = rows["Rod"]
    assert rod.unit_price is None and rod.hsn_code is None and rod.unit == "pcs"
    assert len(rod.issues) == 4  # price ≤ 0, GST missing, bad HSN, unit assumed


def test_preview_matches_existing_items_by_exact_name_only():
    existing = [_item("Hex Bolt M10", "4.50"), _item("TMT Rod 12mm", "60")]
    extraction = CatalogExtraction(items=[
        ExtractedCatalogItem(name="hex bolt m10", unit_price=4.5, gst_rate_percent=18),
        ExtractedCatalogItem(name="TMT Rod 12mm", unit_price=64, gst_rate_percent=18),
        ExtractedCatalogItem(name="TMT Rod 10mm", unit_price=58, gst_rate_percent=18),
        ExtractedCatalogItem(name="Hex bolt M10", unit_price=9, gst_rate_percent=18),  # duplicate row
        ExtractedCatalogItem(name="  ", unit_price=1),
    ])
    preview = build_preview(extraction, existing)
    rows = {r.name: r for r in preview.rows}

    assert rows["hex bolt m10"].match == "unchanged"
    assert rows["TMT Rod 12mm"].match == "update"
    assert rows["TMT Rod 12mm"].existing_unit_price == Decimal("60")
    # A different size is a different product, never merged by fuzzy matching.
    assert rows["TMT Rod 10mm"].match == "new"
    assert preview.skipped == 2


def test_unit_aliases():
    assert normalize_unit("Nos") == "pcs"
    assert normalize_unit("per Kg.") == "kg"
    assert normalize_unit("Metres") == "mtr"
    assert normalize_unit("") is None
    assert normalize_unit("drum") == "drum"


def test_csv_with_known_headers_is_parsed_without_the_model():
    content = (
        "﻿Item Name,HSN/SAC,Rate (Rs.),UOM,GST %,Closing Stock\n"
        "Hex Bolt M10,7318,\"1,250.50\",Nos,18%,40\n"
        ",,,,,\n"
        "Washer,,0.80,pcs,,\n"
    ).encode("utf-8")
    extraction = parse_csv_catalog(content)
    assert extraction is not None
    rows = {r.name: r for r in build_preview(extraction, []).rows}
    bolt = rows["Hex Bolt M10"]
    assert (bolt.unit_price, bolt.unit, bolt.gst_rate_percent, bolt.hsn_code, bolt.quantity_available) == \
        (Decimal("1250.50"), "pcs", Decimal("18.00"), "7318", Decimal("40.00"))
    assert rows["Washer"].issues == ["GST rate missing"]


def test_csv_without_recognisable_headers_falls_back():
    assert parse_csv_catalog(b"a,b\n1,2\n") is None
    assert parse_csv_catalog(b"") is None


# ── API ───────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def ctx(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'catalog.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as s:
        s.add_all([
            Tenant(id=TENANT_ID, business_name="Vaidya Industrial Supplies", state="Maharashtra"),
            Tenant(id=OTHER_TENANT_ID, business_name="Other Co", state="Gujarat"),
        ])
        await s.flush()
        bolt = _item("Hex Bolt M10", "4.50")
        theirs = _item("Hex Bolt M10", "99", tenant=OTHER_TENANT_ID)
        s.add_all([bolt, theirs])
        await s.flush()
        s.add(Stock(item_id=bolt.id, tenant_id=TENANT_ID, quantity_available=Decimal("40")))
        await s.commit()

    async def override_session():
        async with factory() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def stub_gemini(monkeypatch):
    calls = []

    def fake_extract(content: bytes, mime_type: str) -> CatalogExtraction:
        calls.append(mime_type)
        return CatalogExtraction(items=[
            ExtractedCatalogItem(name="Hex Bolt M10", unit_price=5, unit="nos", gst_rate_percent=18),
            ExtractedCatalogItem(name="Spring Washer 10mm", unit_price=0.8, unit="pcs", gst_rate_percent=None),
        ], notes="Used the 'Rate' column.")

    monkeypatch.setattr(catalog_import, "_extract_sync", fake_extract)
    return calls


async def test_preview_returns_review_rows_and_writes_nothing(ctx, stub_gemini):
    client, factory = ctx
    resp = await client.post("/api/v1/catalog/import/preview",
                             files={"file": ("list.jpg", PNG_BYTES, "image/jpg")})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert stub_gemini == ["image/jpeg"]
    assert body["notes"] == "Used the 'Rate' column."
    rows = {r["name"]: r for r in body["rows"]}
    assert rows["Hex Bolt M10"]["match"] == "update"
    assert rows["Hex Bolt M10"]["existing_unit_price"] == 4.5  # own tenant's price, not 99
    assert rows["Spring Washer 10mm"]["issues"] == ["GST rate missing"]

    async with factory() as s:
        count = len((await s.execute(select(Item).where(Item.tenant_id == TENANT_ID))).scalars().all())
    assert count == 1


async def test_csv_preview_does_not_call_the_model(ctx, stub_gemini):
    client, _ = ctx
    resp = await client.post("/api/v1/catalog/import/preview",
                             files={"file": ("list.csv", b"Item,Price,GST\nNut M10,1.2,18\n", "text/csv")})
    assert resp.status_code == 200, resp.text
    assert [r["name"] for r in resp.json()["rows"]] == ["Nut M10"]
    assert stub_gemini == []


async def test_preview_rejects_unsupported_files_before_calling_the_model(ctx, stub_gemini):
    client, _ = ctx
    resp = await client.post("/api/v1/catalog/import/preview",
                             files={"file": ("list.xlsx", b"PK\x03\x04", "application/vnd.ms-excel")})
    assert resp.status_code == 422
    assert "photo" in resp.json()["message"]
    assert stub_gemini == []


async def test_preview_rejects_oversized_files(ctx, stub_gemini, monkeypatch):
    client, _ = ctx
    monkeypatch.setattr(catalog_import, "MAX_UPLOAD_BYTES", 16)
    resp = await client.post("/api/v1/catalog/import/preview",
                             files={"file": ("big.png", PNG_BYTES, "image/png")})
    assert resp.status_code == 422
    assert stub_gemini == []


async def test_import_creates_and_updates_items_with_stock(ctx):
    client, factory = ctx
    resp = await client.post("/api/v1/catalog/import", json={"items": [
        {"name": "hex bolt m10", "unit_price": "5.00", "unit": "pcs", "gst_rate_percent": "18"},
        {"name": "Spring Washer 10mm", "unit_price": "0.80", "unit": "Nos", "gst_rate_percent": "18",
         "hsn_code": "73182100", "quantity_available": "250"},
        {"name": "Nut M10", "unit_price": "1.20", "gst_rate_percent": "18"},
    ]})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"created": 2, "updated": 1, "unchanged": 0}

    async with factory() as s:
        rows = (await s.execute(
            select(Item, Stock.quantity_available).outerjoin(Stock, Stock.item_id == Item.id)
            .where(Item.tenant_id == TENANT_ID)
        )).all()
        theirs = (await s.execute(select(Item).where(Item.tenant_id == OTHER_TENANT_ID))).scalar_one()
    by_name = {item.name: (item, qty) for item, qty in rows}
    assert set(by_name) == {"Hex Bolt M10", "Spring Washer 10mm", "Nut M10"}  # existing name kept
    bolt, bolt_qty = by_name["Hex Bolt M10"]
    assert bolt.unit_price == Decimal("5.00") and bolt_qty == Decimal("40")  # stock untouched
    washer, washer_qty = by_name["Spring Washer 10mm"]
    assert (washer.unit, washer.hsn_code, washer_qty) == ("pcs", "73182100", Decimal("250"))
    assert by_name["Nut M10"][1] == Decimal("0")
    assert theirs.unit_price == Decimal("99")

    # Re-importing the same list is a no-op, not a duplicate.
    again = await client.post("/api/v1/catalog/import", json={"items": [
        {"name": "Nut M10", "unit_price": "1.20", "gst_rate_percent": "18"},
    ]})
    assert again.json() == {"created": 0, "updated": 0, "unchanged": 1}


@pytest.mark.parametrize("row", [
    {"name": "X", "unit_price": "10", "gst_rate_percent": "17"},
    {"name": "X", "unit_price": "0", "gst_rate_percent": "18"},
    {"name": "X", "unit_price": "10", "gst_rate_percent": "18", "hsn_code": "12"},
    {"name": "", "unit_price": "10", "gst_rate_percent": "18"},
])
async def test_import_rejects_invalid_rows_and_saves_nothing(ctx, row):
    client, factory = ctx
    resp = await client.post("/api/v1/catalog/import", json={"items": [
        {"name": "Good Item", "unit_price": "5", "gst_rate_percent": "18"}, row,
    ]})
    assert resp.status_code == 422
    async with factory() as s:
        names = (await s.execute(select(Item.name).where(Item.tenant_id == TENANT_ID))).scalars().all()
    assert names == ["Hex Bolt M10"]


async def test_update_business_profile(ctx):
    client, _ = ctx
    resp = await client.patch("/api/v1/business", json={
        "business_name": "  Vaidya Steel  ", "gstin": "27abcde1234f1z5", "address": "Pune",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["business_name"], body["gstin"], body["state"], body["address"]) == \
        ("Vaidya Steel", "27ABCDE1234F1Z5", "Maharashtra", "Pune")

    cleared = (await client.patch("/api/v1/business", json={"gstin": ""})).json()
    assert cleared["gstin"] is None and cleared["business_name"] == "Vaidya Steel"

    assert (await client.patch("/api/v1/business", json={"gstin": "NOTAGSTIN"})).status_code == 422
