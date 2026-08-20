"""
M1M (Munim.ai) — Customer Lookup Service
==========================================
Tenant-scoped fuzzy customer lookup tool for LangGraph agents.

Requirements:
  - Scoped strictly to the specified tenant_id.
  - Matches customer name case-insensitively and handles common variations.
  - Returns Customer model or None if no confident match.
  - Never creates a customer automatically.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


def _normalize_name(text: str) -> str:
    """Normalize string for fuzzy comparison (lower, strip punctuation/spaces)."""
    return re.sub(r"[^\w\s]", "", text).lower().strip()


async def lookup_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
) -> Optional[Customer]:
    """
    Find the best matching customer for a given tenant.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    tenant_id : uuid.UUID
        Tenant to search within.
    name : str
        Customer name extracted from user message.

    Returns
    -------
    Optional[Customer]
        The matching Customer or None.
    """
    raw_query = (name or "").strip()
    if not raw_query:
        return None

    norm_query = _normalize_name(raw_query)
    if not norm_query:
        return None

    # Fetch all customers for the tenant
    stmt = select(Customer).where(Customer.tenant_id == tenant_id)
    result = await session.execute(stmt)
    customers = list(result.scalars().all())

    if not customers:
        return None

    # 1. Exact match (case-insensitive)
    for c in customers:
        if c.name.strip().lower() == raw_query.lower():
            return c

    # 2. Normalized exact match
    for c in customers:
        if _normalize_name(c.name) == norm_query:
            return c

    # 3. Substring match (either query in customer name or customer name in query)
    best_candidate: Optional[Customer] = None
    best_score = 0.0

    query_tokens = set(norm_query.split())

    for c in customers:
        c_norm = _normalize_name(c.name)
        c_tokens = set(c_norm.split())

        # Check full containment
        if norm_query in c_norm or c_norm in norm_query:
            score = len(norm_query) / max(len(c_norm), 1)
            if score > best_score:
                best_score = score
                best_candidate = c
            continue

        # Check token overlap
        overlap = query_tokens.intersection(c_tokens)
        if overlap:
            score = len(overlap) / max(len(query_tokens.union(c_tokens)), 1)
            if score > 0.4 and score > best_score:
                best_score = score
                best_candidate = c

    if best_candidate and (best_score >= 0.4 or norm_query in _normalize_name(best_candidate.name)):
        return best_candidate

    return None


async def create_customer_if_missing(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
) -> Customer:
    """
    Create a new customer if it doesn't exist (fuzzy match failed).
    
    Parameters
    ----------
    session : AsyncSession
        Active database session.
    tenant_id : uuid.UUID
        Tenant to create customer for.
    name : str
        Customer name.
    
    Returns
    -------
    Customer
        The newly created customer or existing match.
    """
    # First try to find existing customer
    existing = await lookup_customer(session, tenant_id, name)
    if existing:
        return existing
    
    # Create new customer
    new_customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name.strip(),
        phone=None,
        gstin=None,
        state=None,
        address=None,
    )
    session.add(new_customer)
    await session.flush()  # Get the ID assigned without committing
    return new_customer
