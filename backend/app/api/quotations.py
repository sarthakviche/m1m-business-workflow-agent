"""
quotations.py — /quotations CRUD and PDF routes.
"""

from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, set_tenant_context
from app.models.quotation import Quotation, QuotationLine
from app.models.user import AppUser
from app.models.customer import Customer
from app.models.item import Item
from app.services.pdf_generator import generate_quotation_pdf_bytes

router = APIRouter()


class QuotationLineCreate(BaseModel):
    item_id: UUID
    quantity: Decimal


class QuotationCreate(BaseModel):
    customer_id: UUID
    quotation_number: str
    lines: list[QuotationLineCreate]


@router.post("/")
async def create_quotation(
    quotation_data: QuotationCreate,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Create a quotation and quotation lines."""
    res = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    res_cust = await db.execute(select(Customer).where(Customer.id == quotation_data.customer_id))
    customer = res_cust.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")

    quotation = Quotation(
        tenant_id=user.tenant_id,
        customer_id=quotation_data.customer_id,
        quotation_number=quotation_data.quotation_number,
        status="draft",
    )
    db.add(quotation)
    await db.flush()

    subtotal = Decimal("0")

    for line_in in quotation_data.lines:
        res_item = await db.execute(select(Item).where(Item.id == line_in.item_id))
        item = res_item.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {line_in.item_id} not found.")

        unit_price = Decimal(str(item.unit_price))
        line_total = line_in.quantity * unit_price
        subtotal += line_total

        line = QuotationLine(
            tenant_id=user.tenant_id,
            quotation_id=quotation.id,
            item_id=item.id,
            quantity=line_in.quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        db.add(line)

    quotation.subtotal = subtotal
    await db.commit()
    await db.refresh(quotation)

    return {
        "id": str(quotation.id),
        "tenant_id": str(quotation.tenant_id),
        "customer_id": str(quotation.customer_id),
        "quotation_number": quotation.quotation_number,
        "subtotal": float(quotation.subtotal),
        "status": quotation.status,
        "created_at": quotation.created_at,
    }


@router.get("/")
async def get_quotations(
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """List all quotations belonging to the tenant."""
    res = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    res_q = await db.execute(
        select(Quotation)
        .where(Quotation.tenant_id == user.tenant_id)
        .order_by(Quotation.created_at.desc())
    )
    quotations = res_q.scalars().all()

    output = []
    for q in quotations:
        res_c = await db.execute(select(Customer).where(Customer.id == q.customer_id))
        customer = res_c.scalar_one_or_none()
        cust_name = customer.name if customer else "Unknown"

        output.append({
            "id": str(q.id),
            "tenant_id": str(q.tenant_id),
            "customer_id": str(q.customer_id),
            "customer_name": cust_name,
            "quotation_number": q.quotation_number,
            "subtotal": float(q.subtotal) if q.subtotal is not None else 0.0,
            "status": q.status,
            "created_at": q.created_at,
        })
    return output


@router.get("/{quotation_id}")
async def get_quotation(
    quotation_id: str,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve single quotation with line items and customer info."""
    res = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)

    try:
        q_uuid = UUID(quotation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid quotation UUID format.")

    res_q = await db.execute(
        select(Quotation).where(
            Quotation.id == q_uuid,
            Quotation.tenant_id == user.tenant_id
        )
    )
    quotation = res_q.scalar_one_or_none()
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    res_c = await db.execute(select(Customer).where(Customer.id == quotation.customer_id))
    customer = res_c.scalar_one_or_none()

    res_lines = await db.execute(select(QuotationLine).where(QuotationLine.quotation_id == quotation.id))
    lines = res_lines.scalars().all()

    formatted_lines = []
    for l in lines:
        res_i = await db.execute(select(Item).where(Item.id == l.item_id))
        item = res_i.scalar_one_or_none()
        formatted_lines.append({
            "id": str(l.id),
            "item_id": str(l.item_id),
            "item_name": item.name if item else "Item",
            "hsn_code": item.hsn_code if item else "N/A",
            "unit": item.unit if item else "Pcs",
            "quantity": float(l.quantity),
            "unit_price": float(l.unit_price),
            "line_total": float(l.line_total),
        })

    return {
        "id": str(quotation.id),
        "tenant_id": str(quotation.tenant_id),
        "customer_id": str(quotation.customer_id),
        "customer_name": customer.name if customer else "Unknown",
        "customer_phone": customer.phone if customer else None,
        "quotation_number": quotation.quotation_number,
        "subtotal": float(quotation.subtotal) if quotation.subtotal is not None else 0.0,
        "status": quotation.status,
        "created_at": quotation.created_at,
        "lines": formatted_lines,
    }


@router.get("/{quotation_id}/pdf")
async def get_quotation_pdf(
    quotation_id: str,
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return Quotation PDF file."""
    q_data = await get_quotation(quotation_id=quotation_id, phone=phone, db=db)
    
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
    
    res_c = await db.execute(select(Customer).where(Customer.id == UUID(q_data["customer_id"])))
    customer = res_c.scalar_one_or_none()
    cust_dict = {
        "name": customer.name if customer else "Customer",
        "phone": customer.phone if customer else "",
        "address": customer.address if customer else "",
        "gstin": customer.gstin if customer else "",
    } if customer else {}

    lines = q_data.get("lines", [])
    pdf_bytes = generate_quotation_pdf_bytes(q_data, cust_dict, lines, tenant_dict)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=quotation_{q_data['quotation_number']}.pdf"
        }
    )
