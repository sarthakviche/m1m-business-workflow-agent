"""
M1M (Munim.ai) — Quotation Service
====================================
Deterministic quotation creation and database persistence.

Requirements:
  - Calculate each line total deterministically: round2(unit_price × quantity).
  - Calculate quotation subtotal deterministically.
  - Generate quotation number using Q-{YYYYMM}-{sequential}.
  - Create Quotation (status="draft") and QuotationLine rows.
  - Generate PDF quotation and store local reference in quotation.pdf_url.
  - No Gemini arithmetic or external API calls.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.item import Item
from app.models.quotation import Quotation, QuotationLine
from app.models.tenant import Tenant
from app.services.doc_number import generate_quotation_number
from app.services.pdf_service import generate_quotation_pdf

_CENT = Decimal("0.01")


def _round2(val: Decimal) -> Decimal:
    return val.quantize(_CENT, rounding=ROUND_HALF_UP)


async def create_quotation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer: Customer,
    items_with_qty: List[Tuple[Item, Decimal]],
) -> Dict[str, Any]:
    """
    Create a new Quotation with lines, save to DB, and generate PDF.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    tenant_id : uuid.UUID
        Tenant ID.
    customer : Customer
        Resolved Customer model.
    items_with_qty : List[Tuple[Item, Decimal]]
        List of (Item model, quantity).

    Returns
    -------
    Dict[str, Any]
        Dictionary with quotation_id, quotation_number, customer_name,
        subtotal, pdf_url, lines, response_text.
    """
    # Fetch tenant details for PDF
    tenant_res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found.")

    # 1. Compute lines and subtotal deterministically
    line_records: List[Dict[str, Any]] = []
    subtotal = Decimal("0.00")

    for item, qty in items_with_qty:
        qty_dec = Decimal(str(qty))
        price_dec = Decimal(str(item.unit_price))
        line_total = _round2(price_dec * qty_dec)
        subtotal += line_total

        line_records.append({
            "item_id": item.id,
            "item_name": item.name,
            "hsn_code": item.hsn_code,
            "quantity": qty_dec,
            "unit": item.unit,
            "unit_price": price_dec,
            "line_total": line_total,
        })

    # 2. Generate quotation number
    quote_num = await generate_quotation_number(session, tenant_id)

    # 3. Create Quotation record
    quotation = Quotation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        quotation_number=quote_num,
        status="draft",
        subtotal=subtotal,
        pdf_url=None,
    )
    session.add(quotation)
    await session.flush()

    # 4. Create QuotationLine records
    for line_data in line_records:
        q_line = QuotationLine(
            id=uuid.uuid4(),
            quotation_id=quotation.id,
            item_id=line_data["item_id"],
            quantity=line_data["quantity"],
            unit_price=line_data["unit_price"],
            line_total=line_data["line_total"],
        )
        session.add(q_line)

    # 5. Generate PDF
    pdf_url = generate_quotation_pdf(tenant, customer, quotation, line_records)
    quotation.pdf_url = pdf_url

    await session.flush()

    # Format human-readable response text
    items_desc = ", ".join(f"{l['quantity']}x {l['item_name']} (₹{l['unit_price']:.2f})" for l in line_records)
    response_text = (
        f"Quotation **{quote_num}** created for **{customer.name}**.\n"
        f"• Items: {items_desc}\n"
        f"• Subtotal: ₹{subtotal:.2f}\n"
        f"• Status: Draft"
    )

    return {
        "quotation_id": str(quotation.id),
        "quotation_number": quote_num,
        "customer_name": customer.name,
        "customer_id": str(customer.id),
        "subtotal": float(subtotal),
        "pdf_url": pdf_url,
        "lines": line_records,
        "response_text": response_text,
    }
