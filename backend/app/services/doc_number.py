"""
M1M (Munim.ai) — Document Number Generation Service
=====================================================
Formats:
  - Quotation: Q-{YYYYMM}-{sequential:03d}   (e.g., Q-202608-001)
  - Invoice:   INV-{YYYYMM}-{sequential:03d} (e.g., INV-202608-001)

Numbers come from an atomic counter row per business and month. The row stays
locked until the transaction ends, so simultaneous requests wait their turn, and
a rolled-back document gives its number back. GST invoices must be consecutive,
so this avoids both duplicates and gaps.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.upsert import upsert_insert
from app.models.document import DocumentSequence
from app.models.invoice import Invoice
from app.models.quotation import Quotation


async def _highest_issued(session: AsyncSession, column, tenant_column, tenant_id: uuid.UUID, prefix: str) -> int:
    """Highest number already issued, for documents older than the counter table."""
    rows = await session.execute(select(column).where(tenant_column == tenant_id, column.like(f"{prefix}%")))
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    return max((int(m.group(1)) for m in map(pattern.match, rows.scalars()) if m), default=0)


async def _next_number(session: AsyncSession, column, tenant_column, tenant_id: uuid.UUID, prefix: str) -> str:
    start = await _highest_issued(session, column, tenant_column, tenant_id, prefix) + 1
    statement = upsert_insert(session, DocumentSequence).values(tenant_id=tenant_id, prefix=prefix, last_number=start)
    statement = statement.on_conflict_do_update(
        index_elements=["tenant_id", "prefix"],
        set_={"last_number": DocumentSequence.last_number + 1},
    ).returning(DocumentSequence.last_number)
    number = (await session.execute(statement)).scalar_one()
    return f"{prefix}{number:03d}"


async def generate_quotation_number(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dt: datetime | None = None,
) -> str:
    """Next quotation number for the tenant: Q-YYYYMM-XXX."""
    prefix = f"Q-{(dt or datetime.now()).strftime('%Y%m')}-"
    return await _next_number(session, Quotation.quotation_number, Quotation.tenant_id, tenant_id, prefix)


async def generate_invoice_number(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dt: datetime | None = None,
) -> str:
    """Next invoice number for the tenant: INV-YYYYMM-XXX."""
    prefix = f"INV-{(dt or datetime.now()).strftime('%Y%m')}-"
    return await _next_number(session, Invoice.invoice_number, Invoice.tenant_id, tenant_id, prefix)
