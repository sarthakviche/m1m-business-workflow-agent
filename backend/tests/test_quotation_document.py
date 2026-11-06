"""
Tests for the customer-facing quotation document: Indian number formatting,
the GST estimate, the rendered template content and the PDF renderer chain.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import pdf_service
from app.services.number_format import amount_in_words, format_inr, format_quantity

TENANT = SimpleNamespace(id=uuid.uuid4(), business_name="Vaidya Industrial Supplies", gstin="27AABCV1234A1Z5",
                         state="Maharashtra", address="Plot 45, MIDC, Pune")
LOCAL = SimpleNamespace(name="Ramesh Traders", state="Maharashtra", gstin="27AABCR1001A1Z3",
                        address="Bhawani Peth, Pune", phone="+919900000001")
DELHI = SimpleNamespace(name="Delhi Industrial Corporation", state="Delhi", gstin=None, address=None, phone=None)
NO_STATE = SimpleNamespace(name="Walk-in Buyer", state=None, gstin=None, address=None, phone=None)

LINES = [
    {"item_name": "TMT Steel Rod 12mm", "hsn_code": "7213", "quantity": Decimal("10"), "unit": "kg",
     "unit_price": Decimal("58.00"), "line_total": Decimal("580.00"), "gst_rate_percent": Decimal("18")},
    {"item_name": "Safety Helmet IS:2925", "hsn_code": "6506", "quantity": Decimal("4"), "unit": "pcs",
     "unit_price": Decimal("350.00"), "line_total": Decimal("1400.00"), "gst_rate_percent": Decimal("5")},
]
QUOTATION = SimpleNamespace(quotation_number="Q-202611-007", subtotal=Decimal("1980.00"), status="draft")


@pytest.mark.parametrize("value, expected", [
    (0, "0.00"), (999, "999.00"), (4230.5, "4,230.50"), (100000, "1,00,000.00"),
    (1234567.891, "12,34,567.89"), (Decimal("-1500"), "-1,500.00"),
])
def test_format_inr_uses_indian_grouping(value, expected):
    assert format_inr(value) == expected


@pytest.mark.parametrize("value, expected", [
    (Decimal("10.00"), "10"), (Decimal("12.50"), "12.5"), (Decimal("1000"), "1000"), (0.25, "0.25"),
])
def test_format_quantity_drops_trailing_zeros(value, expected):
    assert format_quantity(value) == expected


@pytest.mark.parametrize("value, expected", [
    (0, "Rupees Zero Only"),
    (580, "Rupees Five Hundred Eighty Only"),
    (Decimal("2112.90"), "Rupees Two Thousand One Hundred Twelve and Ninety Paise Only"),
    (100000, "Rupees One Lakh Only"),
    (Decimal("12345678.05"), "Rupees One Crore Twenty Three Lakh Forty Five Thousand Six Hundred Seventy Eight and Five Paise Only"),
])
def test_amount_in_words_uses_lakh_and_crore(value, expected):
    assert amount_in_words(value) == expected


def test_tax_estimate_intra_state_groups_by_rate():
    tax = pdf_service.tax_breakdown(TENANT, LOCAL, LINES)
    assert tax["inter_state"] is False
    assert [(g["rate"], g["cgst"], g["sgst"], g["igst"]) for g in tax["groups"]] == [
        (Decimal("5"), Decimal("35.00"), Decimal("35.00"), Decimal("0.00")),
        (Decimal("18"), Decimal("52.20"), Decimal("52.20"), Decimal("0.00")),
    ]
    assert tax["total_tax"] == Decimal("174.40")
    assert tax["grand_total"] == Decimal("2154.40")


def test_tax_estimate_inter_state_uses_igst():
    tax = pdf_service.tax_breakdown(TENANT, DELHI, LINES)
    assert tax["inter_state"] is True
    assert [g["igst"] for g in tax["groups"]] == [Decimal("70.00"), Decimal("104.40")]
    assert tax["place_of_supply"] == "Delhi"


def test_tax_estimate_assumes_supplier_state_when_customer_has_none():
    tax = pdf_service.tax_breakdown(TENANT, NO_STATE, LINES)
    assert tax["state_assumed"] is True and tax["inter_state"] is False


def test_tax_estimate_is_skipped_without_gst_rates():
    lines = [{**LINES[0], "gst_rate_percent": None}]
    assert pdf_service.tax_breakdown(TENANT, LOCAL, lines) is None


def test_rendered_quotation_is_customer_facing():
    html = pdf_service.render_quotation_html(TENANT, LOCAL, QUOTATION, LINES, issued=datetime(2026, 11, 3))
    for expected in (
        "Vaidya Industrial Supplies", "Q-202611-007", "03 Nov 2026", "03 Dec 2026",   # 30-day validity
        "10 kg", "1,400.00", "CGST @ 9%", "SGST @ 2.5%", "2,154.40",
        "Rupees Two Thousand One Hundred Fifty Four and Forty Paise Only",
        "Authorised signatory",
    ):
        assert expected in html, expected
    # Internal workflow details never reach the customer.
    assert "draft" not in html.lower()
    assert "M1M Agent" not in html


def test_rendered_inter_state_quotation_shows_igst_only():
    html = pdf_service.render_quotation_html(TENANT, DELHI, QUOTATION, LINES)
    assert "IGST @ 18%" in html and "CGST @" not in html


def test_renderer_falls_back_to_minimal_pdf_in_development(monkeypatch):
    monkeypatch.setattr(pdf_service, "_weasyprint", lambda: None)
    monkeypatch.setattr(pdf_service, "_render_with_browser", lambda html, path: False)
    assert pdf_service._render_pdf("<p>x</p>", "QUOTATION Q-1", ["line"]).startswith(b"%PDF-1.4")


def test_production_never_issues_a_text_only_document(monkeypatch):
    monkeypatch.setattr(pdf_service, "_weasyprint", lambda: None)
    monkeypatch.setattr(pdf_service, "_render_with_browser", lambda html, path: False)
    monkeypatch.setattr(pdf_service, "get_settings", lambda: SimpleNamespace(is_development=False))
    with pytest.raises(pdf_service.DocumentRenderError):
        pdf_service._render_pdf("<p>x</p>", "TAX INVOICE INV-1", ["line"])


def test_renderer_prefers_weasyprint(monkeypatch):
    calls = []

    class FakeHTML:
        def __init__(self, string):
            calls.append(string)

        def write_pdf(self):
            return b"%PDF-weasy"

    monkeypatch.setattr(pdf_service, "_weasyprint", lambda: SimpleNamespace(HTML=FakeHTML))
    monkeypatch.setattr(pdf_service, "_render_with_browser", lambda html, path: pytest.fail("browser not needed"))
    assert pdf_service._render_pdf("<p>x</p>", "t", []) == b"%PDF-weasy"
    assert calls == ["<p>x</p>"]


# ─── Tax invoice ─────────────────────────────────────────────────────────────

INVOICE = SimpleNamespace(invoice_number="INV-202611-003", subtotal=Decimal("1980.00"), cgst_amount=Decimal("87.20"),
                          sgst_amount=Decimal("87.20"), igst_amount=Decimal("0.00"), total_amount=Decimal("2154.40"),
                          status="unpaid", due_date=None)


def test_rendered_invoice_uses_stored_totals_and_links_quotation():
    html = pdf_service.render_invoice_html(TENANT, LOCAL, INVOICE, LINES, quotation_number="Q-202611-007",
                                           issued=datetime(2026, 11, 3))
    for expected in (
        "TAX INVOICE", "Original for recipient", "INV-202611-003", "Against quotation", "Q-202611-007",
        "Bill to", "Reverse charge", "CGST @ 2.5%", "SGST @ 9%", "174.40", "2,154.40",
        "Rupees Two Thousand One Hundred Fifty Four and Forty Paise Only",
    ):
        assert expected in html, expected
    assert "unpaid" not in html.lower()
    assert "Due date" not in html  # no due date stored, none invented


def test_invoice_breakdown_matches_stored_invoice_totals():
    tax = pdf_service.tax_breakdown(TENANT, LOCAL, LINES)
    assert tax["total_tax"] == INVOICE.cgst_amount + INVOICE.sgst_amount
    assert tax["grand_total"] == INVOICE.total_amount


def test_rendered_invoice_shows_due_date_when_set():
    from datetime import date

    invoice = SimpleNamespace(**{**vars(INVOICE), "due_date": date(2026, 12, 3)})
    html = pdf_service.render_invoice_html(TENANT, DELHI, invoice, LINES)
    assert "Due date" in html and "03 Dec 2026" in html
    assert "IGST @ 18%" in html and "Against quotation" not in html
