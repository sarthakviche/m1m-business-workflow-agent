"""Tenant-scoped, deterministic business insight queries for chat."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.item import Item
from app.models.payment import Payment
from app.models.stock import Stock

BusinessPeriod = Literal["today", "this_week", "this_month", "last_month"]
# India Standard Time is a fixed UTC+5:30 with no daylight saving. A fixed
# offset avoids ZoneInfo, which needs a timezone database that Windows and
# slim Docker images don't ship (it crashed tool registration at startup).
KOLKATA = timezone(timedelta(hours=5, minutes=30), "IST")
LOW_STOCK_THRESHOLD = Decimal("10")


@dataclass(frozen=True)
class SalesSummary:
    total: Decimal
    invoice_count: int


@dataclass(frozen=True)
class OutstandingDue:
    customer_name: str
    amount: Decimal


@dataclass(frozen=True)
class LowStockItem:
    name: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class TopCustomer:
    name: str
    total: Decimal


def period_bounds(period: BusinessPeriod, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return an inclusive-start, exclusive-end interval in Asia/Kolkata time."""
    local_now = (now or datetime.now(KOLKATA)).astimezone(KOLKATA)
    today = local_now.date()
    start = datetime.combine(today, time.min, tzinfo=KOLKATA)

    if period == "today":
        return start, start + timedelta(days=1)
    if period == "this_week":
        start -= timedelta(days=start.weekday())
        return start, start + timedelta(days=7)
    if period == "this_month":
        start = start.replace(day=1)
        return start, _next_month(start)
    if period == "last_month":
        this_month = start.replace(day=1)
        previous_month_end = this_month - timedelta(days=1)
        previous_month = previous_month_end.replace(day=1)
        return previous_month, this_month
    raise ValueError(f"Unsupported business period: {period}")


def _next_month(value: datetime) -> datetime:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)


def period_label(period: BusinessPeriod) -> str:
    return {
        "today": "today",
        "this_week": "this week",
        "this_month": "this month",
        "last_month": "last month",
    }[period]


async def sales_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    period: BusinessPeriod,
    now: datetime | None = None,
) -> SalesSummary:
    """Return issued invoice sales and count for one business and period."""
    start, end = period_bounds(period, now)
    total, count = (await session.execute(
        select(
            func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")),
            func.count(Invoice.id),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.created_at >= start,
            Invoice.created_at < end,
        )
    )).one()
    return SalesSummary(total=Decimal(total or 0), invoice_count=int(count or 0))


async def outstanding_dues(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 3,
) -> list[OutstandingDue]:
    """Return customers with the highest positive unpaid invoice balances."""
    paid_by_invoice = (
        select(Payment.invoice_id, func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label("paid"))
        .group_by(Payment.invoice_id)
        .subquery()
    )
    remaining = Invoice.total_amount - func.coalesce(paid_by_invoice.c.paid, Decimal("0.00"))
    total_remaining = func.sum(remaining)
    rows = (await session.execute(
        select(Customer.name, total_remaining.label("remaining"))
        .join(Invoice, Invoice.customer_id == Customer.id)
        .outerjoin(paid_by_invoice, paid_by_invoice.c.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Customer.tenant_id == tenant_id,
            Invoice.status.in_(("unpaid", "partially_paid")),
            remaining > Decimal("0.00"),
        )
        .group_by(Customer.id, Customer.name)
        .having(total_remaining > Decimal("0.00"))
        .order_by(total_remaining.desc(), Customer.name)
        .limit(limit)
    )).all()
    return [OutstandingDue(customer_name=name, amount=Decimal(amount)) for name, amount in rows]


async def low_stock_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    threshold: Decimal = LOW_STOCK_THRESHOLD,
    limit: int = 10,
) -> list[LowStockItem]:
    """Return low-stock catalog items for one business."""
    rows = (await session.execute(
        select(Item.name, Stock.quantity_available, Item.unit)
        .join(Stock, Stock.item_id == Item.id)
        .where(
            Item.tenant_id == tenant_id,
            Stock.tenant_id == tenant_id,
            Stock.quantity_available <= threshold,
        )
        .order_by(Stock.quantity_available, Item.name)
        .limit(limit)
    )).all()
    return [LowStockItem(name=name, quantity=Decimal(quantity), unit=unit) for name, quantity, unit in rows]


async def top_customers(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    period: BusinessPeriod,
    now: datetime | None = None,
    limit: int = 3,
) -> list[TopCustomer]:
    """Return the highest-billing customers for one business and period."""
    start, end = period_bounds(period, now)
    rows = (await session.execute(
        select(Customer.name, func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")).label("total"))
        .join(Invoice, Invoice.customer_id == Customer.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Customer.tenant_id == tenant_id,
            Invoice.created_at >= start,
            Invoice.created_at < end,
        )
        .group_by(Customer.id, Customer.name)
        .order_by(func.sum(Invoice.total_amount).desc(), Customer.name)
        .limit(limit)
    )).all()
    return [TopCustomer(name=name, total=Decimal(total)) for name, total in rows]
