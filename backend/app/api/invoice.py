"""
invoice.py — /invoices CRUD, dues, and PDF routes.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, set_tenant_context
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment
from app.models.user import AppUser
from app.models.customer import Customer
from app.models.item import Item
from app.services.pdf_generator import generate_invoice_pdf_bytes


router = APIRouter()


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class InvoiceLineCreate(BaseModel):
    item_id: UUID
    quantity: Decimal


class InvoiceCreate(BaseModel):
    customer_id: UUID
    invoice_number: str
    due_date: date | None = None
    lines: list[InvoiceLineCreate]


class InvoiceUpdate(BaseModel):
    customer_id: UUID
    invoice_number: str
    due_date: date | None = None
    status: str
    tally_push_status: str


# ---------------------------------------------------------
# GET DUES SUMMARY (Must be placed before /{invoice_id})
# ---------------------------------------------------------

@router.get("/dues")
async def get_invoice_dues(
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Calculate dues, payments, and outstanding amount from real database data."""
    res = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    res_inv = await db.execute(
        select(Invoice).where(Invoice.tenant_id == user.tenant_id)
    )
    invoices = res_inv.scalars().all()

    total_invoiced = sum((inv.total_amount or Decimal("0") for inv in invoices), Decimal("0"))

    # Payments sum
    res_pay = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.tenant_id == user.tenant_id)
    )
    total_paid = Decimal(str(res_pay.scalar() or 0))

    outstanding_amount = total_invoiced - total_paid

    unpaid_count = sum(1 for inv in invoices if inv.status == "unpaid")
    partially_paid_count = sum(1 for inv in invoices if inv.status == "partially_paid")
    paid_count = sum(1 for inv in invoices if inv.status == "paid")

    today = date.today()
    overdue_count = sum(1 for inv in invoices if inv.due_date and inv.due_date < today and inv.status != "paid")

    return {
        "tenant_id": str(user.tenant_id),
        "total_invoiced": float(total_invoiced),
        "total_paid": float(total_paid),
        "outstanding_amount": float(outstanding_amount),
        "unpaid_count": unpaid_count,
        "partially_paid_count": partially_paid_count,
        "paid_count": paid_count,
        "overdue_count": overdue_count,
        "total_invoices_count": len(invoices),
    }


# ---------------------------------------------------------
# CREATE INVOICE
# ---------------------------------------------------------

@router.post("/")
async def create_invoice(
    invoice_data: InvoiceCreate,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Create an invoice and its invoice lines."""
    result = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    result = await db.execute(select(Customer).where(Customer.id == invoice_data.customer_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")

    invoice = Invoice(
        tenant_id=user.tenant_id,
        customer_id=invoice_data.customer_id,
        invoice_number=invoice_data.invoice_number,
        due_date=invoice_data.due_date,
    )
    db.add(invoice)
    await db.flush()

    subtotal = Decimal("0")
    cgst_amount = Decimal("0")
    sgst_amount = Decimal("0")
    igst_amount = Decimal("0")

    for line_data in invoice_data.lines:
        result = await db.execute(select(Item).where(Item.id == line_data.item_id))
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {line_data.item_id} not found.")

        quantity = line_data.quantity
        unit_price = Decimal(str(item.unit_price))
        gst_rate = Decimal(str(item.gst_rate_percent))

        line_total = quantity * unit_price
        gst_amount = line_total * gst_rate / Decimal("100")
        cgst = gst_amount / Decimal("2")
        sgst = gst_amount / Decimal("2")

        subtotal += line_total
        cgst_amount += cgst
        sgst_amount += sgst

        invoice_line = InvoiceLine(
            tenant_id=user.tenant_id,
            invoice_id=invoice.id,
            item_id=item.id,
            quantity=quantity,
            unit_price=unit_price,
            gst_rate_percent=gst_rate,
            line_total=line_total,
        )
        db.add(invoice_line)

    invoice.subtotal = subtotal
    invoice.cgst_amount = cgst_amount
    invoice.sgst_amount = sgst_amount
    invoice.igst_amount = igst_amount
    invoice.total_amount = subtotal + cgst_amount + sgst_amount + igst_amount

    await db.commit()
    await db.refresh(invoice)

    return {
        "id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "customer_id": str(invoice.customer_id),
        "invoice_number": invoice.invoice_number,
        "subtotal": float(invoice.subtotal),
        "cgst_amount": float(invoice.cgst_amount),
        "sgst_amount": float(invoice.sgst_amount),
        "igst_amount": float(invoice.igst_amount),
        "total_amount": float(invoice.total_amount),
        "status": invoice.status,
        "due_date": invoice.due_date,
        "pdf_url": invoice.pdf_url,
        "tally_push_status": invoice.tally_push_status,
        "created_at": invoice.created_at,
    }


# ---------------------------------------------------------
# GET ALL INVOICES
# ---------------------------------------------------------

@router.get("/")
async def get_invoices(
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all invoices belonging to the user's tenant with customer names."""
    result = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    result = await db.execute(
        select(Invoice)
        .where(Invoice.tenant_id == user.tenant_id)
        .order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()

    output = []
    for invoice in invoices:
        res_c = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
        customer = res_c.scalar_one_or_none()
        cust_name = customer.name if customer else "Unknown"

        output.append({
            "id": str(invoice.id),
            "tenant_id": str(invoice.tenant_id),
            "customer_id": str(invoice.customer_id),
            "customer_name": cust_name,
            "invoice_number": invoice.invoice_number,
            "subtotal": float(invoice.subtotal) if invoice.subtotal is not None else None,
            "cgst_amount": float(invoice.cgst_amount),
            "sgst_amount": float(invoice.sgst_amount),
            "igst_amount": float(invoice.igst_amount),
            "total_amount": float(invoice.total_amount) if invoice.total_amount is not None else None,
            "status": invoice.status,
            "due_date": invoice.due_date,
            "pdf_url": invoice.pdf_url,
            "tally_push_status": invoice.tally_push_status,
            "created_at": invoice.created_at,
        })

    return output


# ---------------------------------------------------------
# GET ONE INVOICE
# ---------------------------------------------------------

@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve single invoice with line items and customer details."""
    result = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    try:
        inv_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid invoice UUID format.")

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == inv_uuid,
            Invoice.tenant_id == user.tenant_id,
        )
    )
    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    # Customer info
    res_c = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
    customer = res_c.scalar_one_or_none()

    # Invoice line items
    res_lines = await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id))
    lines = res_lines.scalars().all()

    formatted_lines = []
    for l in lines:
        res_i = await db.execute(select(Item).where(Item.id == l.item_id))
        item = res_i.scalar_one_or_none()
        formatted_lines.append({
            "id": str(l.id),
            "item_id": str(l.item_id),
            "item_name": item.name if item else "Item",
            "quantity": float(l.quantity),
            "unit_price": float(l.unit_price),
            "gst_rate_percent": float(l.gst_rate_percent),
            "line_total": float(l.line_total),
        })

    return {
        "id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "customer_id": str(invoice.customer_id),
        "customer_name": customer.name if customer else "Unknown",
        "customer_phone": customer.phone if customer else None,
        "customer_gstin": customer.gstin if customer else None,
        "customer_address": customer.address if customer else None,
        "invoice_number": invoice.invoice_number,
        "subtotal": float(invoice.subtotal) if invoice.subtotal is not None else None,
        "cgst_amount": float(invoice.cgst_amount),
        "sgst_amount": float(invoice.sgst_amount),
        "igst_amount": float(invoice.igst_amount),
        "total_amount": float(invoice.total_amount) if invoice.total_amount is not None else None,
        "status": invoice.status,
        "due_date": invoice.due_date,
        "pdf_url": invoice.pdf_url,
        "tally_push_status": invoice.tally_push_status,
        "created_at": invoice.created_at,
        "lines": formatted_lines,
    }


# ---------------------------------------------------------
# GET INVOICE PDF
# ---------------------------------------------------------

@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return Invoice PDF file."""
    inv_data = await get_invoice(invoice_id=invoice_id, phone=phone, db=db)

    res = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res.scalar_one_or_none()

    tenant_dict = {}
    if user:
        from app.models.tenant import Tenant
        res_t = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant_obj = res_t.scalar_one_or_none()
        if tenant_obj:
            tenant_dict = {
                "name": tenant_obj.business_name,
                "phone": user.phone,
                "address": tenant_obj.address,
                "gstin": tenant_obj.gstin,
                "state": tenant_obj.state,
            }

    res_c = await db.execute(select(Customer).where(Customer.id == UUID(inv_data["customer_id"])))
    customer = res_c.scalar_one_or_none()
    cust_dict = {
        "name": customer.name if customer else "Customer",
        "phone": customer.phone if customer else "",
        "address": customer.address if customer else "",
        "gstin": customer.gstin if customer else "",
        "state": customer.state if customer else "",
    } if customer else {}

    lines = inv_data.get("lines", [])
    pdf_bytes = generate_invoice_pdf_bytes(inv_data, cust_dict, lines, tenant_dict)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=invoice_{inv_data['invoice_number']}.pdf"
        }
    )


# ---------------------------------------------------------
# UPDATE INVOICE
# ---------------------------------------------------------

@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: UUID,
    invoice_data: InvoiceUpdate,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Update an invoice belonging to the user's tenant."""
    result = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == user.tenant_id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    result = await db.execute(
        select(Customer).where(
            Customer.id == invoice_data.customer_id,
            Customer.tenant_id == user.tenant_id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")

    if invoice_data.status not in {"unpaid", "partially_paid", "paid"}:
        raise HTTPException(status_code=400, detail="Invalid invoice status.")

    if invoice_data.tally_push_status not in {"not_applicable", "pending", "pushed"}:
        raise HTTPException(status_code=400, detail="Invalid tally push status.")

    invoice.customer_id = invoice_data.customer_id
    invoice.invoice_number = invoice_data.invoice_number
    invoice.due_date = invoice_data.due_date
    invoice.status = invoice_data.status
    invoice.tally_push_status = invoice_data.tally_push_status

    await db.commit()
    await db.refresh(invoice)

    return {
        "id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "customer_id": str(invoice.customer_id),
        "invoice_number": invoice.invoice_number,
        "subtotal": float(invoice.subtotal) if invoice.subtotal is not None else None,
        "cgst_amount": float(invoice.cgst_amount),
        "sgst_amount": float(invoice.sgst_amount),
        "igst_amount": float(invoice.igst_amount),
        "total_amount": float(invoice.total_amount) if invoice.total_amount is not None else None,
        "status": invoice.status,
        "due_date": invoice.due_date,
        "pdf_url": invoice.pdf_url,
        "tally_push_status": invoice.tally_push_status,
        "created_at": invoice.created_at,
    }


# ---------------------------------------------------------
# DELETE INVOICE
# ---------------------------------------------------------

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: UUID,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Delete an invoice belonging to the user's tenant."""
    result = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == user.tenant_id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    await db.delete(invoice)
    await db.commit()

    return {"message": "Invoice deleted successfully."}