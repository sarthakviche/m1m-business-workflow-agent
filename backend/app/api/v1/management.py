from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any

from app.db.session import AsyncSessionLocal
from app.models.customer import Customer
from app.models.item import Item
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.config import get_settings

router = APIRouter()

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

def get_tenant_id():
    return get_settings().effective_sprint_tenant_id

@router.get("/dashboard/summary")
async def get_dashboard_summary(phone: str, session: AsyncSession = Depends(get_db_session)):
    tenant_id = get_tenant_id()
    return {
        "total_revenue": 125000,
        "unpaid_dues": 45000,
        "pending_quotations": 12,
        "low_stock_items": 3
    }

@router.get("/customers/")
async def list_customers(phone: str, session: AsyncSession = Depends(get_db_session)):
    tenant_id = get_tenant_id()
    stmt = select(Customer).where(Customer.tenant_id == tenant_id)
    result = await session.execute(stmt)
    customers = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "gstin": c.gstin
        } for c in customers
    ]

@router.get("/items/")
async def list_items(phone: str, session: AsyncSession = Depends(get_db_session)):
    tenant_id = get_tenant_id()
    stmt = select(Item).where(Item.tenant_id == tenant_id)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "code": str(i.id),
            "name": i.name,
            "category": getattr(i, 'category', 'General'),
            "price": float(i.unit_price),
            "stock": getattr(i, 'stock', 0),
            "unit": i.unit
        } for i in items
    ]

@router.get("/invoices/")
async def list_invoices(phone: str, session: AsyncSession = Depends(get_db_session)):
    tenant_id = get_tenant_id()
    stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
    result = await session.execute(stmt)
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "number": d.document_number,
            "customer_name": getattr(d, 'customer_name', 'Customer'), 
            "total": float(d.grand_total) if getattr(d, 'grand_total', None) else 0.0,
            "status": getattr(d, 'status', 'pending'),
            "date": d.created_at.strftime("%Y-%m-%d")
        } for d in docs
    ]

@router.get("/quotations/")
async def list_quotations(phone: str, session: AsyncSession = Depends(get_db_session)):
    tenant_id = get_tenant_id()
    stmt = select(Quotation).where(Quotation.tenant_id == tenant_id)
    result = await session.execute(stmt)
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "number": d.document_number,
            "customer_name": getattr(d, 'customer_name', 'Customer'),
            "total": float(d.total_amount) if getattr(d, 'total_amount', None) else 0.0,
            "status": getattr(d, 'status', 'pending'),
            "date": d.created_at.strftime("%Y-%m-%d")
        } for d in docs
    ]
