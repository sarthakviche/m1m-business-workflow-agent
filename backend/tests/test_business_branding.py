"""Tests for tenant-owned document logos and brand colours."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models
import app.api.v1.account as account_api
from app.auth.dependencies import get_request_context
from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.models.document import DocumentFile
from app.models.tenant import Tenant
from app.orchestrator.context import RequestContext
from app.services import pdf_service

TENANT_ID = uuid.UUID(get_settings().effective_sprint_tenant_id)
OTHER_TENANT_ID = uuid.UUID("c0ffee00-aaaa-4bbb-8ccc-eeeeeeeeeeee")
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest_asyncio.fixture
async def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'branding.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add_all([
            Tenant(id=TENANT_ID, business_name="Vaidya Supplies", state="Maharashtra"),
            Tenant(id=OTHER_TENANT_ID, business_name="Other Co", state="Gujarat", brand_color="#123456"),
        ])
        await session.commit()

    async def override_session():
        async with factory() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http, factory
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


async def test_logo_upload_replaces_stored_content_and_is_tenant_scoped(client):
    http, factory = client
    uploaded = await http.post("/api/v1/business/logo", files={"file": ("logo.png", PNG_BYTES, "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["logo_url"] == "/api/v1/business/logo"

    replacement = b"\xff\xd8\xff" + b"\x00" * 32
    replaced = await http.post("/api/v1/business/logo", files={"file": ("logo.jpg", replacement, "image/jpeg")})
    assert replaced.status_code == 200, replaced.text
    response = await http.get("/api/v1/business/logo")
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content == replacement

    async with factory() as session:
        session.add(DocumentFile(
            tenant_id=OTHER_TENANT_ID,
            doc_type="business_assets",
            filename="logo",
            content=PNG_BYTES,
        ))
        await session.commit()

    async def other_business_context() -> RequestContext:
        return RequestContext(business_id=OTHER_TENANT_ID, conversation_id=uuid.uuid4(), channel="web")

    fastapi_app.dependency_overrides[get_request_context] = other_business_context
    other_logo = await http.get("/api/v1/business/logo")
    assert other_logo.status_code == 200
    assert other_logo.content == PNG_BYTES
    fastapi_app.dependency_overrides.pop(get_request_context)

    # The default business can only retrieve its own replacement, never tenant B's asset.
    own_logo = await http.get("/api/v1/business/logo")
    assert own_logo.content == replacement


@pytest.mark.parametrize("content, media_type", [
    (b"not-an-image", "image/png"),
    (b"GIF89a" + b"\x00" * 20, "image/gif"),
])
async def test_logo_upload_rejects_untrusted_file_types(client, content, media_type):
    http, _ = client
    response = await http.post("/api/v1/business/logo", files={"file": ("logo", content, media_type)})
    assert response.status_code == 422
    assert "PNG or JPEG" in response.json()["message"]


async def test_logo_upload_rejects_files_larger_than_one_mb(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(account_api, "_LOGO_MAX_BYTES", 16)
    response = await http.post("/api/v1/business/logo", files={"file": ("logo.png", PNG_BYTES, "image/png")})
    assert response.status_code == 422
    assert "1 MB" in response.json()["message"]


async def test_brand_colour_validates_and_returns_only_current_tenant_branding(client):
    http, _ = client
    response = await http.patch("/api/v1/business/branding", json={"brand_color": "#Fef3C7"})
    assert response.status_code == 200, response.text
    assert response.json()["brand_color"] == "#fef3c7"
    assert (await http.get("/api/v1/business/branding")).json()["brand_color"] == "#fef3c7"
    assert (await http.patch("/api/v1/business/branding", json={"brand_color": "orange"})).status_code == 422


def test_pdf_templates_render_optional_logo_and_readable_brand_colour():
    tenant = SimpleNamespace(
        business_name="Vaidya Supplies", state="Maharashtra", gstin=None, address=None,
        brand_color="#fef3c7",
    )
    customer = SimpleNamespace(name="Buyer", state="Maharashtra", gstin=None, address=None, phone=None)
    quotation = SimpleNamespace(quotation_number="Q-202611-001", subtotal=Decimal("100"), status="draft")
    invoice = SimpleNamespace(
        invoice_number="INV-202611-001", subtotal=Decimal("100"), cgst_amount=Decimal("9"),
        sgst_amount=Decimal("9"), igst_amount=Decimal("0"), total_amount=Decimal("118"), due_date=None,
    )
    lines = [{"item_name": "Bolt", "hsn_code": "7318", "quantity": Decimal("1"), "unit": "pcs", "unit_price": Decimal("100"), "line_total": Decimal("100"), "gst_rate_percent": Decimal("18")}]
    logo = "data:image/png;base64,AAAA"

    quotation_html = pdf_service.render_quotation_html(tenant, customer, quotation, lines, logo_data_url=logo)
    invoice_html = pdf_service.render_invoice_html(tenant, customer, invoice, lines)

    assert logo in quotation_html
    assert "class=\"monogram\"" not in quotation_html
    assert "class=\"monogram\"" in invoice_html
    assert "background: #fef3c7; color: #111827" in quotation_html
