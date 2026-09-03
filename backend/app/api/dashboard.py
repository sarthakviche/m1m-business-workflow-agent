"""
dashboard.py — /dashboard/summary route.
"""

from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, set_tenant_context
from app.models.user import AppUser
from app.models.customer import Customer
from app.models.item import Item
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.payment import Payment

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(
    phone: str = Query(..., description="Development: phone number of user"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve real tenant business metrics from PostgreSQL/Supabase database."""
    res_user = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res_user.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)
    tid = user.tenant_id

    # 1. Total Customers
    res_cust = await db.execute(select(func.count(Customer.id)).where(Customer.tenant_id == tid))
    total_customers = res_cust.scalar() or 0

    # 2. Total Items
    res_item = await db.execute(select(func.count(Item.id)).where(Item.tenant_id == tid))
    total_items = res_item.scalar() or 0

    # 3. Invoices metrics
    res_inv = await db.execute(select(Invoice).where(Invoice.tenant_id == tid))
    invoices = res_inv.scalars().all()
    total_invoices = len(invoices)

    total_sales = sum((inv.total_amount or Decimal("0") for inv in invoices), Decimal("0"))
    paid_invoices_count = sum(1 for inv in invoices if inv.status == "paid")
    unpaid_invoices_count = sum(1 for inv in invoices if inv.status == "unpaid")
    partially_paid_count = sum(1 for inv in invoices if inv.status == "partially_paid")

    today = date.today()
    overdue_count = sum(1 for inv in invoices if inv.due_date and inv.due_date < today and inv.status != "paid")

    # 4. Total Quotations
    res_q = await db.execute(select(func.count(Quotation.id)).where(Quotation.tenant_id == tid))
    total_quotations = res_q.scalar() or 0

    # 5. Total Paid & Outstanding Amount
    res_pay = await db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.tenant_id == tid))
    total_paid_amount = Decimal(str(res_pay.scalar() or 0))

    outstanding_amount = total_sales - total_paid_amount

    return {
        "tenant_id": str(tid),
        "total_customers": total_customers,
        "total_items": total_items,
        "total_invoices": total_invoices,
        "total_quotations": total_quotations,
        "total_sales": float(total_sales),
        "total_paid_amount": float(total_paid_amount),
        "outstanding_amount": float(outstanding_amount),
        "paid_invoices_count": paid_invoices_count,
        "unpaid_invoices_count": unpaid_invoices_count,
        "partially_paid_count": partially_paid_count,
        "overdue_invoices_count": overdue_count,
    }
