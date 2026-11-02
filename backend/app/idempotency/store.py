"""
Munim.ai — Idempotency Store (Phase 4)
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class IdempotencyStore:
    """
    Ensures safe retry of write operations.
    If a tool has already successfully completed for a given idempotency_key,
    it returns the cached result instead of executing again.
    
    Phase 4 stub: uses a simple in-memory dict for local testing until
    the full `idempotency_log` table is added via Alembic.
    """
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def _get_cache_key(self, key: str, business_id: uuid.UUID) -> str:
        return f"{business_id}::{key}"

    async def get(
        self,
        idempotency_key: str,
        business_id: uuid.UUID,
        session: AsyncSession,
    ) -> Dict[str, Any] | None:
        return self._store.get(self._get_cache_key(idempotency_key, business_id))

    async def set(
        self,
        idempotency_key: str,
        business_id: uuid.UUID,
        status: Literal["processing", "completed", "failed"],
        result: Any = None,
        session: AsyncSession = None,
    ) -> None:
        self._store[self._get_cache_key(idempotency_key, business_id)] = {
            "status": status,
            "result": result,
        }

idempotency_store = IdempotencyStore()
