"""
M1M (Munim.ai) — Item Lookup Service
======================================
Tenant-scoped fuzzy item catalog lookup tool for LangGraph agents.

Requirements:
  - Scoped strictly to the specified tenant_id.
  - Matches item name case-insensitively and handles common variations.
  - Returns Item model (id, name, hsn_code, gst_rate_percent, unit_price, unit) or None.
  - Never invents an item, price, or GST rate.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item


def _normalize_name(text: str) -> str:
    """Normalize string for fuzzy comparison (lower, strip punctuation/spaces)."""
    return re.sub(r"[^\w\s]", "", text).lower().strip()


async def lookup_item(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
) -> Optional[Item]:
    """
    Find the best matching catalog item for a given tenant.

    Parameters
    ----------
    session : AsyncSession
        Active database session.
    tenant_id : uuid.UUID
        Tenant to search within.
    name : str
        Item name extracted from user message.

    Returns
    -------
    Optional[Item]
        The matching Item or None.
    """
    raw_query = (name or "").strip()
    if not raw_query:
        return None

    norm_query = _normalize_name(raw_query)
    if not norm_query:
        return None

    stmt = select(Item).where(Item.tenant_id == tenant_id)
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    if not items:
        return None

    # 1. Exact match (case-insensitive)
    for it in items:
        if it.name.strip().lower() == raw_query.lower():
            return it

    # 2. Normalized exact match
    for it in items:
        if _normalize_name(it.name) == norm_query:
            return it

    # 3. Substring / token matching
    best_candidate: Optional[Item] = None
    best_score = 0.0

    query_tokens = set(norm_query.split())

    for it in items:
        it_norm = _normalize_name(it.name)
        it_tokens = set(it_norm.split())

        # Check full containment
        if norm_query in it_norm or it_norm in norm_query:
            score = len(norm_query) / max(len(it_norm), 1)
            if score > best_score:
                best_score = score
                best_candidate = it
            continue

        # Check token overlap
        overlap = query_tokens.intersection(it_tokens)
        if overlap:
            score = len(overlap) / max(len(query_tokens.union(it_tokens)), 1)
            if score > 0.3 and score > best_score:
                best_score = score
                best_candidate = it

    if best_candidate and (best_score >= 0.3 or norm_query in _normalize_name(best_candidate.name)):
        return best_candidate

    return None
