"""
M1M (Munim.ai) — PDF Generation Service
=========================================
Generates Quotation and Tax Invoice PDFs using Jinja2 HTML templates
and WeasyPrint.

Per TRD Section 7:
  - Templates in `app/templates/quotation.html` and `invoice.html`.
  - Renders Jinja2 HTML → PDF.
  - Stores PDFs locally in Sprint 1 under `generated_docs/{tenant_id}/{doc_type}/`.
"""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
import uuid

import jinja2

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

    template = _jinja_env.get_template("quotation.html")
    rendered_html = template.render(
        tenant=tenant,
        customer=customer,
        quotation=quotation,
        lines=lines,
        date_str=datetime.now().strftime("%d-%b-%Y"),
    )

    try:
        import weasyprint
        weasyprint.HTML(string=rendered_html).write_pdf(target=str(file_path))
    except Exception:
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
        pdf_bytes = _generate_minimal_pdf_bytes(f"QUOTATION {quotation.quotation_number}", summary_lines)
        file_path.write_bytes(pdf_bytes)

    return f"/documents/{tenant_id_str}/quotations/{quotation.quotation_number}.pdf"


def generate_invoice_pdf(
    tenant: Any,
    customer: Any,
    invoice: Any,
    lines: List[Dict[str, Any]],
    tax_type_label: str = "Intra-State (CGST + SGST)",
) -> str:
    """
    Render Invoice Jinja2 HTML template and output a PDF file.

    Returns the file path / URL string to the generated PDF.
    """
    tenant_id_str = str(tenant.id)
    out_dir = _DOCS_DIR / tenant_id_str / "invoices"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{invoice.invoice_number}.pdf"

    template = _jinja_env.get_template("invoice.html")
    rendered_html = template.render(
        tenant=tenant,
        customer=customer,
        invoice=invoice,
        lines=lines,
        tax_type_label=tax_type_label,
        date_str=datetime.now().strftime("%d-%b-%Y"),
    )

    try:
        import weasyprint
        weasyprint.HTML(string=rendered_html).write_pdf(target=str(file_path))
    except Exception:
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
        pdf_bytes = _generate_minimal_pdf_bytes(f"TAX INVOICE {invoice.invoice_number}", summary_lines)
        file_path.write_bytes(pdf_bytes)

    return f"/documents/{tenant_id_str}/invoices/{invoice.invoice_number}.pdf"
