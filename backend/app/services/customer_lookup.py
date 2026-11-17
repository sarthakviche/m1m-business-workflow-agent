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

import difflib
import re
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


@dataclass
class CustomerMatchResult:
    customer: Optional[Customer]
    score: float
    match_type: str  # "exact", "fuzzy_high", "fuzzy_medium", "none"


def _normalize_name(text: str) -> str:
    """Normalize string for fuzzy comparison (lower, strip punctuation/spaces)."""
    return re.sub(r"[^\w\s]", "", text).lower().strip()


async def lookup_customer_scored(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
) -> CustomerMatchResult:
    """
    Find matching customer with explicit similarity scoring.

    Bands:
      - Exact match / normalized exact -> score=1.0, match_type="exact"
      - Score > 0.8 -> match_type="fuzzy_high" (auto-match)
      - Score 0.4 to 0.8 -> match_type="fuzzy_medium" (requires confirmation)
      - Score < 0.4 -> match_type="none" (auto-create as new)
    """
    raw_query = (name or "").strip()
    if not raw_query:
        return CustomerMatchResult(customer=None, score=0.0, match_type="none")

    norm_query = _normalize_name(raw_query)
    if not norm_query:
        return CustomerMatchResult(customer=None, score=0.0, match_type="none")

    # Fetch all customers for the tenant
    stmt = select(Customer).where(Customer.tenant_id == tenant_id)
    result = await session.execute(stmt)
    customers = list(result.scalars().all())

    if not customers:
        return CustomerMatchResult(customer=None, score=0.0, match_type="none")

    # 1. Exact match (case-insensitive)
    for c in customers:
        if c.name.strip().lower() == raw_query.lower() or _normalize_name(c.name) == norm_query:
            return CustomerMatchResult(customer=c, score=1.0, match_type="exact")

    # 2. Fuzzy match calculation
    best_candidate: Optional[Customer] = None
    best_score = 0.0

    query_tokens = set(norm_query.split())

    for c in customers:
        c_norm = _normalize_name(c.name)
        c_tokens = set(c_norm.split())

        # SequenceMatcher ratio for character similarity
        seq_ratio = difflib.SequenceMatcher(None, norm_query, c_norm).ratio()

        # Token overlap ratio (Jaccard)
        overlap = query_tokens.intersection(c_tokens)
        token_ratio = len(overlap) / max(len(query_tokens.union(c_tokens)), 1) if overlap else 0.0

        # Substring containment ratio
        containment_ratio = 0.0
        if norm_query in c_norm or c_norm in norm_query:
            containment_ratio = min(len(norm_query), len(c_norm)) / max(len(norm_query), len(c_norm), 1)

        # If multi-word query has no token overlap, apply penalty to seq_ratio
        if len(query_tokens) > 1 and len(c_tokens) > 1 and not overlap:
            effective_seq = seq_ratio * 0.5
        else:
            effective_seq = seq_ratio

        candidate_score = max(effective_seq, token_ratio, containment_ratio)

        if candidate_score > best_score:
            best_score = candidate_score
            best_candidate = c

    if best_candidate:
        if best_score > 0.8:
            return CustomerMatchResult(customer=best_candidate, score=best_score, match_type="fuzzy_high")
        elif best_score >= 0.4:
            return CustomerMatchResult(customer=best_candidate, score=best_score, match_type="fuzzy_medium")

    return CustomerMatchResult(customer=None, score=best_score, match_type="none")


async def lookup_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
) -> Optional[Customer]:
    """
    Backward-compatible customer lookup: returns customer only if confident match (> 0.8 or exact).
    """
    match_result = await lookup_customer_scored(session, tenant_id, name)
    if match_result.match_type in ("exact", "fuzzy_high"):
        return match_result.customer
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
