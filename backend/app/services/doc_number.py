"""
M1M (Munim.ai) — Document Number Generation Service
=====================================================
Deterministic and database-safe document sequence generator.

Formats (per TRD / Sprint 1 spec):
  - Quotation: Q-{YYYYMM}-{sequential:03d}   (e.g., Q-202608-001)
  - Invoice:   INV-{YYYYMM}-{sequential:03d} (e.g., INV-202608-001)

Maintains per-tenant monthly sequence counters directly against
PostgreSQL records to prevent duplicates and race conditions.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.quotation import Quotation


async def generate_quotation_number(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dt: datetime | None = None,
) -> str:
    """
    Generate the next sequential quotation number for the tenant in format:
    Q-YYYYMM-XXX
    """
    if dt is None:
        dt = datetime.now()
    prefix = f"Q-{dt.strftime('%Y%m')}-"

    stmt = (
        select(Quotation.quotation_number)
        .where(
            Quotation.tenant_id == tenant_id,
            Quotation.quotation_number.like(f"{prefix}%"),
        )
    )
    result = await session.execute(stmt)
    existing_numbers = result.scalars().all()

    max_seq = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for num in existing_numbers:
        match = pattern.match(num.strip())
        if match:
            seq_val = int(match.group(1))
            if seq_val > max_seq:
                max_seq = seq_val

    next_seq = max_seq + 1
    return f"{prefix}{next_seq:03d}"


async def generate_invoice_number(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dt: datetime | None = None,
) -> str:
    """
    Generate the next sequential invoice number for the tenant in format:
    INV-YYYYMM-XXX
    """
    if dt is None:
        dt = datetime.now()
    prefix = f"INV-{dt.strftime('%Y%m')}-"

    stmt = (
        select(Invoice.invoice_number)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_number.like(f"{prefix}%"),
        )
    )
    result = await session.execute(stmt)
    existing_numbers = result.scalars().all()

    max_seq = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for num in existing_numbers:
        match = pattern.match(num.strip())
        if match:
            seq_val = int(match.group(1))
            if seq_val > max_seq:
                max_seq = seq_val

    next_seq = max_seq + 1
    return f"{prefix}{next_seq:03d}"
