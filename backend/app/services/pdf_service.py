"""
M1M (Munim.ai) — PDF Generation Service
=========================================
Generates Quotation and Tax Invoice PDFs using Jinja2 HTML templates
and WeasyPrint.

Per TRD Section 7:
  - Templates in `app/templates/quotation.html` and `invoice.html`.
  - Renders Jinja2 HTML → PDF.
  - Stores PDFs locally in Sprint 1 under `generated_docs/{tenant_id}/{doc_type}/`.

Renderer chain (first that works wins):
  1. WeasyPrint — production. Needs the Pango system libraries
     (Debian/Ubuntu: apt install libpango-1.0-0 libpangoft2-1.0-0).
  2. Headless Chromium / Chrome / Edge print-to-PDF — renders the same
     template where those libraries are missing (e.g. a Windows dev machine).
     Set PDF_BROWSER_PATH to choose the browser binary.
  3. A minimal text-only PDF, so a document is never lost.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import jinja2

from app.services.gst_calculator import GSTValidationError, calculate_invoice_totals, calculate_line_tax
from app.services.number_format import amount_in_words, format_inr, format_quantity

logger = logging.getLogger(__name__)

# ─── Template & Output Paths ──────────────────────────────────────────────────
_SERVICES_DIR = Path(__file__).resolve().parent
_APP_DIR = _SERVICES_DIR.parent
_BACKEND_DIR = _APP_DIR.parent
_TEMPLATES_DIR = _APP_DIR / "templates"
_DOCS_DIR = _BACKEND_DIR / "generated_docs"
_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Jinja2 environment
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)
_jinja_env.filters["inr"] = format_inr
_jinja_env.filters["qty"] = format_quantity

QUOTATION_VALIDITY_DAYS = 30

_PDF_URL_PREFIX = "/documents/"


def resolve_pdf_path(pdf_url: str | None, tenant_id: uuid.UUID) -> Path | None:
    """
    Map a ``/documents/{tenant_id}/{doc_type}/{file}.pdf`` URL back to the
    generated file. Returns None unless the file exists, belongs to
    ``tenant_id`` and stays inside the documents root.
    """
    if not pdf_url or not pdf_url.startswith(_PDF_URL_PREFIX) or not pdf_url.lower().endswith(".pdf"):
        return None
    relative = pdf_url[len(_PDF_URL_PREFIX):]
    if relative.split("/", 1)[0] != str(tenant_id):
        return None
    root = _DOCS_DIR.resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root / str(tenant_id))
    except ValueError:
        return None
    return target if target.is_file() else None


# ─── Rendering ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _weasyprint():
    """The weasyprint module, or None when its system libraries are missing (checked once)."""
    try:
        import weasyprint
        return weasyprint
    except Exception:  # OSError when Pango cannot be loaded
        logger.warning("pdf.weasyprint_unavailable: using headless browser rendering")
        return None


_BROWSER_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome", "msedge")
_WINDOWS_BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


@lru_cache(maxsize=1)
def _find_browser() -> Optional[str]:
    configured = os.environ.get("PDF_BROWSER_PATH")
    if configured:
        return configured if Path(configured).is_file() else None
    for name in _BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return next((p for p in _WINDOWS_BROWSER_PATHS if Path(p).is_file()), None)


def _render_with_browser(html: str, file_path: Path) -> bool:
    browser = _find_browser()
    if browser is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "document.html"
        source.write_text(html, encoding="utf-8")
        try:
            subprocess.run(
                [
                    browser,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--no-pdf-header-footer",
                    # A private profile, so an already-open browser window is never reused.
                    f"--user-data-dir={Path(tmp) / 'profile'}",
                    f"--print-to-pdf={file_path}",
                    source.as_uri(),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("pdf.browser_render_failed: %s", type(exc).__name__)
            return False
    return file_path.is_file() and file_path.stat().st_size > 0


def _write_pdf(html: str, file_path: Path, fallback_title: str, fallback_lines: List[str]) -> None:
    weasyprint = _weasyprint()
    if weasyprint is not None:
        try:
            weasyprint.HTML(string=html).write_pdf(target=str(file_path))
            return
        except Exception:
            logger.exception("pdf.weasyprint_render_failed")
    if _render_with_browser(html, file_path):
        return
    file_path.write_bytes(_generate_minimal_pdf_bytes(fallback_title, fallback_lines))


def _generate_minimal_pdf_bytes(title: str, lines: list[str]) -> bytes:
    """
    Fallback minimal standard PDF 1.4 byte generator if native C libraries
    (Pango/cairo) are not found on the host OS.
    """
    content_lines = ["BT", "/F1 12 Tf", "50 750 Td", f"({title}) Tj", "0 -20 Td"]
    for l in lines[:35]:
        safe = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"({safe}) Tj")
        content_lines.append("0 -15 Td")
    content_lines.append("ET")
    stream_content = "\n".join(content_lines).encode("latin-1", "replace")

    stream_len = len(stream_content)
    pdf_parts = [
        b"%PDF-1.4\n",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii"),
        stream_content,
        b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"xref\n0 6\n0000000000 65535 f \n",
        b"0000000010 00000 n \n",
        b"0000000060 00000 n \n",
        b"0000000117 00000 n \n",
        b"0000000227 00000 n \n",
        b"0000000300 00000 n \n",
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n380\n%%EOF\n",
    ]
    return b"".join(pdf_parts)


# ─── Shared document context ─────────────────────────────────────────────────

def tax_breakdown(tenant: Any, customer: Any, lines: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Per-rate GST for a set of lines, computed with the deterministic invoice
    calculator. Returns None if any line lacks a valid GST rate (the document
    then shows the subtotal only).
    """
    supplier_state = tenant.state
    customer_state = getattr(customer, "state", None) or supplier_state
    results = []
    groups: Dict[Decimal, Dict[str, Decimal]] = {}
    try:
        for line in lines:
            rate = line.get("gst_rate_percent")
            if rate is None:
                return None
            res = calculate_line_tax(line["unit_price"], line["quantity"], rate, supplier_state, customer_state)
            results.append(res)
            group = groups.setdefault(Decimal(str(rate)), {"taxable": Decimal("0"), "cgst": Decimal("0"),
                                                            "sgst": Decimal("0"), "igst": Decimal("0")})
            group["taxable"] += res.taxable_amount
            group["cgst"] += res.cgst
            group["sgst"] += res.sgst
            group["igst"] += res.igst
    except GSTValidationError:
        return None
    if not results:
        return None

    totals = calculate_invoice_totals(results)
    return {
        "inter_state": results[0].tax_type == "inter_state",
        "place_of_supply": customer_state,
        "state_assumed": not getattr(customer, "state", None),
        "groups": [{"rate": rate, "half_rate": rate / 2, **vals} for rate, vals in sorted(groups.items())],
        "total_tax": totals["total_tax"],
        "grand_total": totals["total_amount"],
    }


def _date(value: datetime) -> str:
    return value.strftime("%d %b %Y")


# ─── Quotation ────────────────────────────────────────────────────────────────

def render_quotation_html(
    tenant: Any,
    customer: Any,
    quotation: Any,
    lines: List[Dict[str, Any]],
    issued: Optional[datetime] = None,
) -> str:
    """Quotation with an *estimated* GST breakdown; the tax invoice is final."""
    issued = issued or datetime.now()
    tax = tax_breakdown(tenant, customer, lines)
    subtotal = quotation.subtotal or Decimal("0")
    grand_total = tax["grand_total"] if tax else subtotal
    return _jinja_env.get_template("quotation.html").render(
        tenant=tenant,
        customer=customer,
        quotation=quotation,
        lines=lines,
        tax=tax,
        doc_number=quotation.quotation_number,
        taxable_total=subtotal,
        tax_total=tax["total_tax"] if tax else Decimal("0"),
        grand_total=grand_total,
        amount_words=amount_in_words(grand_total),
        validity_days=QUOTATION_VALIDITY_DAYS,
        date_str=_date(issued),
        valid_until_str=_date(issued + timedelta(days=QUOTATION_VALIDITY_DAYS)),
    )


def generate_quotation_pdf(
    tenant: Any,
    customer: Any,
    quotation: Any,
    lines: List[Dict[str, Any]],
) -> str:
    """
    Render Quotation Jinja2 HTML template and output a PDF file.

    Returns the file path / URL string to the generated PDF.
    """
    tenant_id_str = str(tenant.id)
    out_dir = _DOCS_DIR / tenant_id_str / "quotations"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{quotation.quotation_number}.pdf"

    rendered_html = render_quotation_html(tenant, customer, quotation, lines)

    summary_lines = [
        f"Business: {tenant.business_name} (GSTIN: {tenant.gstin or 'N/A'})",
        f"State: {tenant.state}",
        f"Customer: {customer.name} ({customer.state or 'N/A'})",
        f"Quote Number: {quotation.quotation_number}",
        f"Subtotal: INR {quotation.subtotal:.2f}",
        "--- Line Items ---",
    ]
    for l in lines:
        summary_lines.append(
            f"- {l.get('item_name')}: {l.get('quantity')} {l.get('unit', 'pcs')} @ INR {l.get('unit_price', 0):.2f} = INR {l.get('line_total', 0):.2f}"
        )
    _write_pdf(rendered_html, file_path, f"QUOTATION {quotation.quotation_number}", summary_lines)

    return f"/documents/{tenant_id_str}/quotations/{quotation.quotation_number}.pdf"


# ─── Invoice ──────────────────────────────────────────────────────────────────

def render_invoice_html(
    tenant: Any,
    customer: Any,
    invoice: Any,
    lines: List[Dict[str, Any]],
    quotation_number: Optional[str] = None,
    issued: Optional[datetime] = None,
) -> str:
    """
    Tax invoice. Per-rate rows come from tax_breakdown (same calculator that
    produced the invoice); the totals printed are the stored invoice amounts.
    """
    issued = issued or datetime.now()
    due_date = getattr(invoice, "due_date", None)
    return _jinja_env.get_template("invoice.html").render(
        tenant=tenant,
        customer=customer,
        invoice=invoice,
        lines=lines,
        tax=tax_breakdown(tenant, customer, lines),
        doc_number=invoice.invoice_number,
        quotation_number=quotation_number,
        taxable_total=invoice.subtotal or Decimal("0"),
        tax_total=(invoice.cgst_amount or 0) + (invoice.sgst_amount or 0) + (invoice.igst_amount or 0),
        grand_total=invoice.total_amount or Decimal("0"),
        amount_words=amount_in_words(invoice.total_amount or 0),
        date_str=_date(issued),
        due_date_str=due_date.strftime("%d %b %Y") if due_date else None,
    )


def generate_invoice_pdf(
    tenant: Any,
    customer: Any,
    invoice: Any,
    lines: List[Dict[str, Any]],
    quotation_number: Optional[str] = None,
) -> str:
    """
    Render Invoice Jinja2 HTML template and output a PDF file.

    Returns the file path / URL string to the generated PDF.
    """
    tenant_id_str = str(tenant.id)
    out_dir = _DOCS_DIR / tenant_id_str / "invoices"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{invoice.invoice_number}.pdf"

    rendered_html = render_invoice_html(tenant, customer, invoice, lines, quotation_number=quotation_number)

    summary_lines = [
        f"Business: {tenant.business_name} (GSTIN: {tenant.gstin or 'N/A'})",
        f"State: {tenant.state}",
        f"Customer: {customer.name} ({customer.state or 'N/A'})",
        f"Invoice Number: {invoice.invoice_number}",
        f"Subtotal: INR {invoice.subtotal:.2f}",
        f"CGST: INR {invoice.cgst_amount:.2f} | SGST: INR {invoice.sgst_amount:.2f} | IGST: INR {invoice.igst_amount:.2f}",
        f"Grand Total: INR {invoice.total_amount:.2f}",
        "--- Line Items ---",
    ]
    for l in lines:
        summary_lines.append(
            f"- {l.get('item_name')}: {l.get('quantity')} {l.get('unit', 'pcs')} @ INR {l.get('unit_price', 0):.2f} (GST {l.get('gst_rate_percent')}%) = INR {l.get('line_grand_total', l.get('line_total', 0)):.2f}"
        )
    _write_pdf(rendered_html, file_path, f"TAX INVOICE {invoice.invoice_number}", summary_lines)

    return f"/documents/{tenant_id_str}/invoices/{invoice.invoice_number}.pdf"
