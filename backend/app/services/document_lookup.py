"""
M1M (Munim.ai) — Document lookup
==================================
Read-only, tenant-scoped queries for existing quotations and invoices. Used by
channel commands (/quotations, /invoices, /pdf) so listing documents is a
plain database read and never goes through the LLM.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.quotation import Quotation

DocumentType = Literal["quotation", "invoice"]


@dataclass(frozen=True)
class DocumentSummary:
    document_type: DocumentType
    number: str
    customer_name: str
    total: Decimal
    status: str
    created_at: Optional[datetime]
    pdf_url: Optional[str]


def _quotation_summary(q: Quotation, customer_name: str) -> DocumentSummary:
    return DocumentSummary("quotation", q.quotation_number, customer_name, q.subtotal or Decimal("0"),
                           q.status, q.created_at, q.pdf_url)


def _invoice_summary(inv: Invoice, customer_name: str) -> DocumentSummary:
    return DocumentSummary("invoice", inv.invoice_number, customer_name, inv.total_amount or Decimal("0"),
                           inv.status, inv.created_at, inv.pdf_url)


async def list_recent_documents(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    limit: int = 5,
) -> List[DocumentSummary]:
    if document_type == "quotation":
        stmt = (
            select(Quotation, Customer.name)
            .join(Customer, Quotation.customer_id == Customer.id)
            .where(Quotation.tenant_id == tenant_id)
            .order_by(Quotation.created_at.desc(), Quotation.quotation_number.desc())
            .limit(limit)
        )
        return [_quotation_summary(q, name) for q, name in (await session.execute(stmt)).all()]

    stmt = (
        select(Invoice, Customer.name)
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.tenant_id == tenant_id)
        .order_by(Invoice.created_at.desc(), Invoice.invoice_number.desc())
        .limit(limit)
    )
    return [_invoice_summary(inv, name) for inv, name in (await session.execute(stmt)).all()]


async def find_document_by_number(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    number: str,
) -> Optional[DocumentSummary]:
    """Exact (case-insensitive) lookup of a quotation or invoice number within the tenant."""
    wanted = (number or "").strip().upper()
    if not wanted:
        return None

    q_row = (await session.execute(
        select(Quotation, Customer.name)
        .join(Customer, Quotation.customer_id == Customer.id)
        .where(Quotation.tenant_id == tenant_id, Quotation.quotation_number == wanted)
    )).first()
    if q_row:
        return _quotation_summary(*q_row)

    inv_row = (await session.execute(
        select(Invoice, Customer.name)
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.tenant_id == tenant_id, Invoice.invoice_number == wanted)
    )).first()
    if inv_row:
        return _invoice_summary(*inv_row)
    return None
