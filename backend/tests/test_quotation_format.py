"""Tests for custom quotation formats: reading a sample, keeping it safe, and rendering with it."""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — register all ORM models
from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.errors.categories import ValidationError
from app.main import app as fastapi_app
from app.models.tenant import Tenant
from app.services import pdf_service, quotation_format as qf

TENANT_ID = uuid.UUID(get_settings().effective_sprint_tenant_id)
OTHER_TENANT_ID = uuid.UUID("c0ffee00-aaaa-4bbb-8ccc-eeeeeeeeeeee")

TENANT = SimpleNamespace(id=uuid.uuid4(), business_name="Sarthak Enterprises", gstin=None,
                         state="Maharashtra", address="Pune", brand_color=None, quotation_format=None)
CUSTOMER = SimpleNamespace(name="Devansh traders", state="Maharashtra", gstin=None, address=None, phone=None)
LINES = [{"item_name": "Coca-Cola (330 ml)", "hsn_code": "2202", "quantity": Decimal("5"), "unit": "pcs",
          "unit_price": Decimal("40.00"), "line_total": Decimal("200.00"), "gst_rate_percent": Decimal("18")}]
QUOTATION = SimpleNamespace(quotation_number="Q-202611-002", subtotal=Decimal("200.00"), status="draft")

MODEL_ANSWER = {
    "title": "PROFORMA QUOTATION",
    "party_label": "M/s",
    "date_label": "Dated",
    "columns": [
        {"key": "index", "label": "Sr."},
        {"key": "item", "label": "Description of Goods"},
        {"key": "qty", "label": "Qty"},
        {"key": "unit", "label": "UOM"},
        {"key": "rate", "label": "Rate"},
        {"key": "amount", "label": "Value"},
        {"key": "discount", "label": "Disc %"},  # not a column we can fill
    ],
    "accent_color": "#1F4E79",
    "terms": ["Delivery within 7 days.", "Payment 50% advance."],
    "bank_details": ["HDFC Bank, A/c 50100012345678", "IFSC HDFC0001234"],
    "signatory_label": "Proprietor",
    "validity_days": 15,
    "show_tax_breakdown": False,
    "placeholders": [
        {"label": "Quotation No.", "field": "quotation_number"},
        {"label": "Delivery period", "field": "other"},
        {"label": "Weird", "field": "not-a-field"},
    ],
}


def test_model_answer_becomes_a_clean_format():
    fmt = qf.format_from_extraction(MODEL_ANSWER, "my-quote.pdf")
    assert fmt.title == "PROFORMA QUOTATION"
    assert [c.key for c in fmt.columns] == ["index", "item", "qty", "unit", "rate", "amount"]
    assert fmt.accent_color == "#1f4e79"
    assert fmt.validity_days == 15
    analysis = qf.analysis_for(fmt)
    assert [p.label for p in analysis.supported_placeholders] == ["Quotation No."]
    assert {p.label for p in analysis.unsupported_placeholders} == {"Delivery period", "Weird"}


def test_bad_model_values_fall_back_to_safe_defaults():
    fmt = qf.format_from_extraction(
        {"title": "", "accent_color": "red; background:url(x)", "columns": [{"key": "qty", "label": "Q"}],
         "validity_days": 9999, "terms": ["  ", "x" * 500]},
        None,
    )
    assert fmt.title == "QUOTATION"
    assert fmt.accent_color is None
    assert fmt.validity_days is None
    keys = [c.key for c in fmt.columns]
    assert "item" in keys and keys[-1] == "amount"  # always shown
    assert fmt.terms == ["x" * 200]


def test_custom_format_drives_the_rendered_quotation():
    fmt = qf.format_from_extraction(MODEL_ANSWER, None)
    html = pdf_service.render_quotation_html(TENANT, CUSTOMER, QUOTATION, LINES, issued=datetime(2026, 11, 17), fmt=fmt)
    for text in ("PROFORMA QUOTATION", "M/s", "Dated", "Description of Goods", "UOM", "Value",
                 "Delivery within 7 days.", "IFSC HDFC0001234", "Proprietor", "#1f4e79", "02 Dec 2026"):
        assert text in html, text
    assert "Delivery and freight are charged" not in html  # standard terms replaced
    assert "CGST @" not in html  # breakdown hidden, single GST line instead


def test_format_text_is_escaped_not_executed():
    fmt = qf.QuotationFormat(title="<script>alert(1)</script>", terms=["{{ 7*7 }}"])
    html = pdf_service.render_quotation_html(TENANT, CUSTOMER, QUOTATION, LINES, fmt=fmt)
    assert "<script>alert(1)</script>" not in html
    assert "{{ 7*7 }}" in html and ">49<" not in html


def test_standard_layout_and_invoices_are_unchanged():
    html = pdf_service.render_quotation_html(TENANT, CUSTOMER, QUOTATION, LINES)
    assert "QUOTATION" in html and "Authorised signatory" in html and "Rate (₹)" in html
    invoice = SimpleNamespace(invoice_number="INV-1", subtotal=Decimal("200"), cgst_amount=Decimal("18"),
                              sgst_amount=Decimal("18"), igst_amount=Decimal("0"), total_amount=Decimal("236"),
                              due_date=None)
    tenant = SimpleNamespace(**{**vars(TENANT), "quotation_format": MODEL_ANSWER})
    inv_html = pdf_service.render_invoice_html(tenant, CUSTOMER, invoice, LINES)
    assert "TAX INVOICE" in inv_html and "Taxable (₹)" in inv_html and "PROFORMA" not in inv_html


def test_saved_format_on_tenant_is_used_by_default():
    tenant = SimpleNamespace(**{**vars(TENANT), "quotation_format": qf.format_from_extraction(MODEL_ANSWER, None).model_dump(mode="json")})
    html = pdf_service.render_quotation_html(tenant, CUSTOMER, QUOTATION, LINES)
    assert "PROFORMA QUOTATION" in html


def _docx(paragraphs: list[str]) -> bytes:
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", f"<w:document {ns}><w:body>{body}</w:body></w:document>")
    return buf.getvalue()


def test_word_and_unknown_files_are_sniffed_from_their_bytes():
    docx = _docx(["QUOTATION", "Terms: Delivery in 7 days"])
    mime = qf.sniff_upload(docx, "q.docx")
    assert mime.endswith("wordprocessingml.document")
    assert "Delivery in 7 days" in qf.office_text(docx, mime)
    assert qf.sniff_upload(b"%PDF-1.7 ...", "q.pdf") == "application/pdf"
    with pytest.raises(ValidationError):
        qf.sniff_upload(b"MZ\x90\x00 not a quotation", "q.exe")


@pytest_asyncio.fixture
async def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'format.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add_all([
            Tenant(id=TENANT_ID, business_name="Sarthak Enterprises", state="Maharashtra"),
            Tenant(id=OTHER_TENANT_ID, business_name="Other Co", state="Gujarat"),
        ])
        await session.commit()

    async def override_session():
        async with factory() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test") as http:
        yield http, factory
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


async def test_analyze_save_preview_and_reset(client, monkeypatch):
    http, factory = client
    monkeypatch.setattr(qf, "_analyze_sync", lambda content, mime: MODEL_ANSWER)
    monkeypatch.setattr(pdf_service, "_render_pdf", lambda html, *a: b"%PDF-preview " + html.encode())

    assert (await http.get("/api/v1/business/quotation-format")).json() == {"analysis": None}

    analyzed = await http.post("/api/v1/business/quotation-format/analyze",
                               files={"file": ("quote.pdf", b"%PDF-1.4 sample", "application/pdf")})
    assert analyzed.status_code == 200, analyzed.text
    fmt = analyzed.json()["format"]
    assert fmt["title"] == "PROFORMA QUOTATION" and fmt["source_filename"] == "quote.pdf"
    # Analysing saves nothing.
    assert (await http.get("/api/v1/business/quotation-format")).json() == {"analysis": None}

    preview = await http.post("/api/v1/business/quotation-format/preview", json=fmt)
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "application/pdf"
    assert b"PROFORMA QUOTATION" in preview.content

    saved = await http.put("/api/v1/business/quotation-format", json=fmt)
    assert saved.status_code == 200, saved.text
    current = (await http.get("/api/v1/business/quotation-format")).json()["analysis"]["format"]
    assert current["title"] == "PROFORMA QUOTATION"
    async with factory() as session:
        assert (await session.get(Tenant, OTHER_TENANT_ID)).quotation_format is None

    assert (await http.delete("/api/v1/business/quotation-format")).status_code == 204
    assert (await http.get("/api/v1/business/quotation-format")).json() == {"analysis": None}


async def test_analyze_rejects_files_that_are_not_documents(client):
    http, _ = client
    response = await http.post("/api/v1/business/quotation-format/analyze",
                               files={"file": ("x.exe", b"MZ\x90\x00binary", "application/pdf")})
    assert response.status_code == 422
