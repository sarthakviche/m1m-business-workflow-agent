"""
M1M (Munim.ai) — Catalog & Stock Query Service
================================================
Read-only catalog item lookup, price query, and inventory stock check service.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.stock import Stock
from app.services.item_lookup import lookup_item


async def lookup_catalog_item_details(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    item_name: str,
) -> Dict[str, Any]:
    """
    Look up item details (name, price, GST %, HSN, stock) for a specific catalog item name.
    """
    item = await lookup_item(session, tenant_id, item_name)
    if not item:
        return {"found": False, "query": item_name}

    stock_res = await session.execute(
        select(Stock).where(Stock.item_id == item.id, Stock.tenant_id == tenant_id)
    )
    stock = stock_res.scalar_one_or_none()
    available_qty = float(stock.quantity_available) if stock else 0.0

    return {
        "found": True,
        "item_id": str(item.id),
        "name": item.name,
        "hsn_code": item.hsn_code,
        "gst_rate_percent": float(item.gst_rate_percent),
        "unit_price": float(item.unit_price),
        "unit": item.unit,
        "stock_available": available_qty,
    }


async def list_catalog_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 6,
) -> Dict[str, Any]:
    """
    Fetch all items with stock for tenant, summarized for chat display.
    """
    stmt = (
        select(Item, Stock.quantity_available)
        .outerjoin(Stock, (Stock.item_id == Item.id) & (Stock.tenant_id == tenant_id))
        .where(Item.tenant_id == tenant_id)
        .order_by(Item.name)
    )
    result = await session.execute(stmt)
    rows = result.all()

    total_count = len(rows)
    items_summary = []
    for item, qty in rows[:limit]:
        items_summary.append({
            "name": item.name,
            "unit_price": float(item.unit_price),
            "unit": item.unit,
            "gst_rate_percent": float(item.gst_rate_percent),
            "stock_available": float(qty or 0.0),
        })

    return {
        "total_count": total_count,
        "displayed_items": items_summary,
        "has_more": total_count > limit,
    }
