"""
M1M (Munim.ai) — Invoice Service
==================================
Deterministic invoice creation, GST calculation integration, stock decrement,
and quotation conversion.

Requirements:
  - Support direct invoice and invoice from quotation.
  - Call existing deterministic GST calculator (calculate_line_tax, calculate_invoice_totals).
  - Check stock for all items before writing anything.
  - Insufficient stock -> fail transactionally (no invoice created, no stock change).
  - Decrement stock for invoiced items by exact quantity.
  - Generate invoice number using INV-{YYYYMM}-{sequential}.
  - Generate Invoice PDF and store local reference in invoice.pdf_url.
  - Mark quotation as converted on successful conversion.
  - No Gemini arithmetic.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceLine
from app.models.item import Item
from app.models.quotation import Quotation, QuotationLine
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.services.doc_number import generate_invoice_number
from app.services.gst_calculator import calculate_invoice_totals, calculate_line_tax
from app.services.pdf_service import generate_invoice_pdf

_CENT = Decimal("0.01")


class InsufficientStockError(ValueError):
    """Raised when available stock is less than invoiced quantity."""


class QuotationNotFoundError(ValueError):
    """Raised when quotation to convert is not found or already converted."""


def _round2(val: Decimal) -> Decimal:
    return val.quantize(_CENT, rounding=ROUND_HALF_UP)


async def create_direct_invoice(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer: Customer,
    items_with_qty: List[Tuple[Item, Decimal]],
) -> Dict[str, Any]:
    """
    Create a direct Invoice with lines, apply deterministic GST,
    decrement stock, and generate PDF.

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
        Structured result with invoice_id, invoice_number, totals, lines, pdf_url.
    """
    # Fetch tenant
    tenant_res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found.")

    supplier_state = tenant.state
    customer_state = customer.state or tenant.state

    # 1. Stock Check Phase (Fail-fast before any modification)
    for item, qty in items_with_qty:
        qty_dec = Decimal(str(qty))
        stock_res = await session.execute(
            select(Stock).where(Stock.item_id == item.id, Stock.tenant_id == tenant_id)
        )
        stock_row = stock_res.scalar_one_or_none()
        available = stock_row.quantity_available if stock_row else Decimal("0.00")
        if available < qty_dec:
            raise InsufficientStockError(
                f"Insufficient stock for '{item.name}'. Available: {available} {item.unit}, Requested: {qty_dec} {item.unit}."
            )

    # 2. GST Calculation Phase using existing deterministic GST calculator
    line_gst_results = []
    line_records: List[Dict[str, Any]] = []

    for item, qty in items_with_qty:
        qty_dec = Decimal(str(qty))
        price_dec = Decimal(str(item.unit_price))
        rate_dec = Decimal(str(item.gst_rate_percent))

        gst_res = calculate_line_tax(
            unit_price=price_dec,
            quantity=qty_dec,
            gst_rate_percent=rate_dec,
            supplier_state=supplier_state,
            customer_state=customer_state,
        )
        line_gst_results.append(gst_res)

        line_records.append({
            "item_id": item.id,
            "item_name": item.name,
            "hsn_code": item.hsn_code,
            "quantity": qty_dec,
            "unit": item.unit,
            "unit_price": price_dec,
            "gst_rate_percent": rate_dec,
            "line_total": gst_res.taxable_amount,
            "tax_amount": gst_res.total_tax,
            "line_grand_total": gst_res.grand_total,
        })

    # Aggregate invoice totals
    totals = calculate_invoice_totals(line_gst_results)

    # 3. Stock Decrement Phase
    for item, qty in items_with_qty:
        qty_dec = Decimal(str(qty))
        stock_res = await session.execute(
            select(Stock).where(Stock.item_id == item.id, Stock.tenant_id == tenant_id)
        )
        stock_row = stock_res.scalar_one()
        stock_row.quantity_available -= qty_dec

    # 4. Generate invoice number
    inv_num = await generate_invoice_number(session, tenant_id)

    # 5. Create Invoice record
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer.id,
        quotation_id=None,
        invoice_number=inv_num,
        subtotal=totals["subtotal"],
        cgst_amount=totals["cgst_amount"],
        sgst_amount=totals["sgst_amount"],
        igst_amount=totals["igst_amount"],
        total_amount=totals["total_amount"],
        status="unpaid",
        due_date=None,
        pdf_url=None,
        tally_push_status="not_applicable",
    )
    session.add(invoice)
    await session.flush()

    # 6. Create InvoiceLine records
    for line_data in line_records:
        inv_line = InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            item_id=line_data["item_id"],
            quantity=line_data["quantity"],
            unit_price=line_data["unit_price"],
            gst_rate_percent=line_data["gst_rate_percent"],
            line_total=line_data["line_total"],
        )
        session.add(inv_line)

    # 7. Generate PDF
    tax_type_label = (
        "Intra-State (CGST + SGST)"
        if totals["cgst_amount"] > 0 or totals["sgst_amount"] > 0
        else "Inter-State (IGST)"
    )
    pdf_url = generate_invoice_pdf(
        tenant, customer, invoice, line_records, tax_type_label=tax_type_label
    )
    invoice.pdf_url = pdf_url

    await session.flush()

    # Format human-readable response text
    tax_breakdown = (
        f"CGST: ₹{totals['cgst_amount']:.2f}, SGST: ₹{totals['sgst_amount']:.2f}"
        if totals["igst_amount"] == 0
        else f"IGST: ₹{totals['igst_amount']:.2f}"
    )
    items_desc = ", ".join(f"{l['quantity']}x {l['item_name']}" for l in line_records)
    response_text = (
        f"Tax Invoice **{inv_num}** created for **{customer.name}**.\n"
        f"• Items: {items_desc}\n"
        f"• Taxable Subtotal: ₹{totals['subtotal']:.2f}\n"
        f"• Taxes ({tax_type_label}): {tax_breakdown}\n"
        f"• Grand Total: ₹{totals['total_amount']:.2f}\n"
        f"• Stock decremented successfully."
    )

    return {
        "invoice_id": str(invoice.id),
        "invoice_number": inv_num,
        "customer_name": customer.name,
        "customer_id": str(customer.id),
        "subtotal": float(totals["subtotal"]),
        "cgst_amount": float(totals["cgst_amount"]),
        "sgst_amount": float(totals["sgst_amount"]),
        "igst_amount": float(totals["igst_amount"]),
        "total_tax": float(totals["total_tax"]),
        "total_amount": float(totals["total_amount"]),
        "pdf_url": pdf_url,
        "lines": line_records,
        "response_text": response_text,
    }


async def convert_quotation_to_invoice(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    quotation_identifier: str,
) -> Dict[str, Any]:
    """
    Convert an existing Quotation into a Tax Invoice.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    tenant_id : uuid.UUID
        Tenant ID.
    quotation_identifier : str
        Quotation number (e.g. 'Q-202608-001') or Quotation UUID.

    Returns
    -------
    Dict[str, Any]
        Structured invoice data.
    """
    # 1. Look up quotation
    ident = quotation_identifier.strip()
    stmt = select(Quotation).where(Quotation.tenant_id == tenant_id)
    try:
        quote_uuid = uuid.UUID(ident)
        stmt = stmt.where((Quotation.id == quote_uuid) | (Quotation.quotation_number == ident))
    except ValueError:
        stmt = stmt.where(Quotation.quotation_number == ident)

    result = await session.execute(stmt)
    quotation = result.scalar_one_or_none()

    if not quotation:
        raise QuotationNotFoundError(f"Quotation '{ident}' not found for this business.")

    if quotation.status == "converted":
        raise QuotationNotFoundError(
            f"Quotation '{quotation.quotation_number}' has already been converted to an invoice."
        )

    # 2. Load quotation lines and customer
    cust_res = await session.execute(select(Customer).where(Customer.id == quotation.customer_id))
    customer = cust_res.scalar_one()

    lines_res = await session.execute(
        select(QuotationLine).where(QuotationLine.quotation_id == quotation.id)
    )
    q_lines = list(lines_res.scalars().all())
    if not q_lines:
        raise ValueError(f"Quotation '{quotation.quotation_number}' has no line items.")

    # 3. Load items and build items_with_qty
    items_with_qty: List[Tuple[Item, Decimal]] = []
    for ql in q_lines:
        item_res = await session.execute(select(Item).where(Item.id == ql.item_id))
        item = item_res.scalar_one()
        items_with_qty.append((item, ql.quantity))

    # 4. Create direct invoice (handles stock check, GST calculation, stock decrement)
    inv_data = await create_direct_invoice(
        session=session,
        tenant_id=tenant_id,
        customer=customer,
        items_with_qty=items_with_qty,
    )

    # 5. Link invoice to quotation & mark quotation as converted
    inv_id = uuid.UUID(inv_data["invoice_id"])
    inv_row_res = await session.execute(select(Invoice).where(Invoice.id == inv_id))
    inv_row = inv_row_res.scalar_one()
    inv_row.quotation_id = quotation.id

    quotation.status = "converted"
    await session.flush()

    inv_data["quotation_id"] = str(quotation.id)
    inv_data["quotation_number"] = quotation.quotation_number
    inv_data["response_text"] = (
        f"Quotation **{quotation.quotation_number}** successfully converted to Tax Invoice **{inv_data['invoice_number']}** for **{customer.name}**.\n"
        f"• Total Amount: ₹{inv_data['total_amount']:.2f}\n"
        f"• Stock decremented.\n"
        f"• Quotation status updated to 'converted'."
    )

    return inv_data
