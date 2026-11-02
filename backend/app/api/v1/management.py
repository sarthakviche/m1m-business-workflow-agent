"""
M1M (Munim.ai) — Business management read API
===============================================
Read-only, tenant-scoped endpoints that power the web app screens.

    GET /api/v1/business            Business profile (name, GSTIN, state)
    GET /api/v1/dashboard/summary   Sales, dues, open quotations, low stock, recent documents
    GET /api/v1/customers           Customers with document counts and billed totals
    GET /api/v1/items               Catalog with price, GST, HSN and current stock

The tenant comes from the authenticated RequestContext (X-API-Key), never
from query parameters.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.chat import get_db_session
from app.auth.dependencies import get_request_context
from app.errors.categories import NotFoundError
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.payment import Payment
from app.models.quotation import Quotation
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.orchestrator.context import RequestContext
from app.services.document_lookup import list_recent_documents

router = APIRouter(tags=["management"])

# Items at or below this quantity are flagged as low stock.
LOW_STOCK_THRESHOLD = Decimal("10")
_OPEN_INVOICE_STATUSES = ("unpaid", "partially_paid", "overdue")


class BusinessProfile(BaseModel):
    id: str
    business_name: str
    gstin: Optional[str]
    state: str
    address: Optional[str]


class LowStockItem(BaseModel):
    id: str
    name: str
    unit: str
    quantity_available: float


class RecentDocument(BaseModel):
    document_type: str
    document_number: str
    customer_name: str
    total: float
    status: str
    created_at: Optional[str]
    pdf_url: Optional[str]


class DashboardSummary(BaseModel):
    total_sales: float
    amount_received: float
    outstanding_amount: float
    unpaid_invoices: int
    open_quotations: int
    open_quotations_value: float
    total_customers: int
    total_items: int
    low_stock_threshold: float
    low_stock_items: List[LowStockItem]
    recent_documents: List[RecentDocument]


class CustomerSummary(BaseModel):
    id: str
    name: str
    phone: Optional[str]
    gstin: Optional[str]
    state: Optional[str]
    address: Optional[str]
    quotation_count: int
    invoice_count: int
    total_billed: float


class CatalogItem(BaseModel):
    id: str
    name: str
    hsn_code: Optional[str]
    unit: str
    unit_price: float
    gst_rate_percent: float
    quantity_available: float
    low_stock: bool


def _money(value: Optional[Decimal]) -> float:
    return float(value or 0)


@router.get("/business", response_model=BusinessProfile)
async def get_business(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> BusinessProfile:
    tenant = await session.get(Tenant, context.business_id)
    if tenant is None:
        raise NotFoundError(detail=f"Tenant {context.business_id} not found", user_message="Business not found.")
    return BusinessProfile(
        id=str(tenant.id),
        business_name=tenant.business_name,
        gstin=tenant.gstin,
        state=tenant.state,
        address=tenant.address,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardSummary:
    tenant_id = context.business_id

    total_sales = (await session.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.tenant_id == tenant_id)
    )).scalar_one()
    received = (await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(Invoice.tenant_id == tenant_id)
    )).scalar_one()
    open_billed, unpaid_count = (await session.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0), func.count(Invoice.id))
        .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(_OPEN_INVOICE_STATUSES))
    )).one()
    paid_against_open = (await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(_OPEN_INVOICE_STATUSES))
    )).scalar_one()
    open_q_count, open_q_value = (await session.execute(
        select(func.count(Quotation.id), func.coalesce(func.sum(Quotation.subtotal), 0))
        .where(Quotation.tenant_id == tenant_id, Quotation.status != "converted")
    )).one()
    customer_count = (await session.execute(
        select(func.count(Customer.id)).where(Customer.tenant_id == tenant_id)
    )).scalar_one()
    item_count = (await session.execute(
        select(func.count(Item.id)).where(Item.tenant_id == tenant_id)
    )).scalar_one()
    low_stock_rows = (await session.execute(
        select(Item.id, Item.name, Item.unit, Stock.quantity_available)
        .join(Stock, Stock.item_id == Item.id)
        .where(Item.tenant_id == tenant_id, Stock.quantity_available <= LOW_STOCK_THRESHOLD)
        .order_by(Stock.quantity_available.asc(), Item.name)
    )).all()

    recent = (
        await list_recent_documents(session, tenant_id, "quotation")
        + await list_recent_documents(session, tenant_id, "invoice")
    )
    recent.sort(key=lambda d: (d.created_at is not None, d.created_at), reverse=True)

    return DashboardSummary(
        total_sales=_money(total_sales),
        amount_received=_money(received),
        outstanding_amount=max(_money(open_billed) - _money(paid_against_open), 0.0),
        unpaid_invoices=unpaid_count,
        open_quotations=open_q_count,
        open_quotations_value=_money(open_q_value),
        total_customers=customer_count,
        total_items=item_count,
        low_stock_threshold=float(LOW_STOCK_THRESHOLD),
        low_stock_items=[
            LowStockItem(id=str(i), name=name, unit=unit, quantity_available=float(qty))
            for i, name, unit, qty in low_stock_rows
        ],
        recent_documents=[
            RecentDocument(
                document_type=d.document_type,
                document_number=d.number,
                customer_name=d.customer_name,
                total=float(d.total),
                status=d.status,
                created_at=d.created_at.isoformat() if d.created_at else None,
                pdf_url=d.pdf_url,
            )
            for d in recent[:6]
        ],
    )


@router.get("/customers", response_model=List[CustomerSummary])
async def list_customers(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[CustomerSummary]:
    tenant_id = context.business_id
    quotation_counts = (
        select(Quotation.customer_id, func.count(Quotation.id).label("n"))
        .where(Quotation.tenant_id == tenant_id)
        .group_by(Quotation.customer_id)
        .subquery()
    )
    invoice_totals = (
        select(
            Invoice.customer_id,
            func.count(Invoice.id).label("n"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("billed"),
        )
        .where(Invoice.tenant_id == tenant_id)
        .group_by(Invoice.customer_id)
        .subquery()
    )
    rows = (await session.execute(
        select(Customer, quotation_counts.c.n, invoice_totals.c.n, invoice_totals.c.billed)
        .outerjoin(quotation_counts, quotation_counts.c.customer_id == Customer.id)
        .outerjoin(invoice_totals, invoice_totals.c.customer_id == Customer.id)
        .where(Customer.tenant_id == tenant_id)
        .order_by(Customer.name)
    )).all()
    return [
        CustomerSummary(
            id=str(c.id),
            name=c.name,
            phone=c.phone,
            gstin=c.gstin,
            state=c.state,
            address=c.address,
            quotation_count=q_count or 0,
            invoice_count=i_count or 0,
            total_billed=_money(billed),
        )
        for c, q_count, i_count, billed in rows
    ]


@router.get("/items", response_model=List[CatalogItem])
async def list_items(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[CatalogItem]:
    rows = (await session.execute(
        select(Item, Stock.quantity_available)
        .outerjoin(Stock, Stock.item_id == Item.id)
        .where(Item.tenant_id == context.business_id)
        .order_by(Item.name)
    )).all()
    return [
        CatalogItem(
            id=str(item.id),
            name=item.name,
            hsn_code=item.hsn_code,
            unit=item.unit,
            unit_price=_money(item.unit_price),
            gst_rate_percent=_money(item.gst_rate_percent),
            quantity_available=_money(qty),
            low_stock=(qty or Decimal("0")) <= LOW_STOCK_THRESHOLD,
        )
        for item, qty in rows
    ]
