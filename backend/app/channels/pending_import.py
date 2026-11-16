"""
Munim.ai — Pending catalog imports for chat channels
=====================================================
A price list read in a chat (Telegram today) waits here until the owner taps
Save or Discard. It lives in the ``conversation_state`` table under its own
key, separate from the agent's multi-turn state, and expires with the same
TTL so an abandoned import can never be saved later by a stale button.

Each import carries a short random token that is embedded in its buttons;
a tap only acts if its token matches the current import for that chat.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.store import DEFAULT_STATE_TTL
from app.models.conversation_state import ConversationStateRecord
from app.services.catalog_import import CatalogImportRow, CatalogPreview, PreviewRow

_NAMESPACE = uuid.UUID("b8e2f4a1-3c5d-4e6f-8a9b-0c1d2e3f4a5b")
_KIND = "catalog_import"


def import_key(channel: str, tenant_id: uuid.UUID, chat_id: int | str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{channel}:import:{tenant_id}:{chat_id}")


@dataclass
class PendingRow:
    name: str
    unit_price: Optional[str]
    unit: str
    hsn_code: Optional[str]
    gst_rate_percent: Optional[str]
    quantity_available: Optional[str]
    match: str
    existing_unit_price: Optional[str]

    @classmethod
    def from_preview(cls, row: PreviewRow) -> "PendingRow":
        def s(value: Optional[Decimal]) -> Optional[str]:
            return str(value) if value is not None else None

        return cls(
            name=row.name, unit_price=s(row.unit_price), unit=row.unit, hsn_code=row.hsn_code,
            gst_rate_percent=s(row.gst_rate_percent), quantity_available=s(row.quantity_available),
            match=row.match, existing_unit_price=s(row.existing_unit_price),
        )

    @property
    def has_price(self) -> bool:
        return self.unit_price is not None

    @property
    def needs_gst(self) -> bool:
        return self.has_price and self.gst_rate_percent is None and self.match != "unchanged"

    @property
    def savable(self) -> bool:
        return self.has_price and self.gst_rate_percent is not None and self.match != "unchanged"

    def to_import_row(self) -> CatalogImportRow:
        return CatalogImportRow(
            name=self.name,
            unit_price=Decimal(self.unit_price),
            unit=self.unit,
            hsn_code=self.hsn_code,
            gst_rate_percent=Decimal(self.gst_rate_percent),
            quantity_available=Decimal(self.quantity_available) if self.quantity_available else None,
        )


@dataclass
class PendingImport:
    token: str
    rows: List[PendingRow]
    notes: Optional[str] = None
    skipped: int = 0
    source_message_ids: List[int] = field(default_factory=list)

    @classmethod
    def from_preview(cls, preview: CatalogPreview) -> "PendingImport":
        return cls(
            token=secrets.token_urlsafe(6),
            rows=[PendingRow.from_preview(r) for r in preview.rows],
            notes=preview.notes,
            skipped=preview.skipped,
        )

    @property
    def savable_rows(self) -> List[PendingRow]:
        return [r for r in self.rows if r.savable]

    @property
    def rows_needing_gst(self) -> List[PendingRow]:
        return [r for r in self.rows if r.needs_gst]

    def apply_gst(self, rate: Decimal) -> int:
        rows = self.rows_needing_gst
        for row in rows:
            row.gst_rate_percent = str(rate)
        return len(rows)

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": _KIND, **asdict(self)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["PendingImport"]:
        if data.get("kind") != _KIND:
            return None
        return cls(
            token=data["token"],
            rows=[PendingRow(**r) for r in data.get("rows", [])],
            notes=data.get("notes"),
            skipped=data.get("skipped", 0),
            source_message_ids=list(data.get("source_message_ids", [])),
        )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class PendingImportStore:
    def __init__(self, ttl: timedelta = DEFAULT_STATE_TTL):
        self._ttl = ttl

    async def get(self, session: AsyncSession, key: uuid.UUID, tenant_id: uuid.UUID) -> Optional[PendingImport]:
        record = await session.get(ConversationStateRecord, key)
        if record is None or record.tenant_id != tenant_id:
            return None
        if datetime.now(timezone.utc) - _as_utc(record.updated_at) > self._ttl:
            return None
        return PendingImport.from_dict(record.state)

    async def save(self, session: AsyncSession, key: uuid.UUID, tenant_id: uuid.UUID, pending: PendingImport) -> None:
        now = datetime.now(timezone.utc)
        record = await session.get(ConversationStateRecord, key)
        if record is None:
            session.add(ConversationStateRecord(conversation_id=key, tenant_id=tenant_id,
                                                state=pending.to_dict(), updated_at=now))
        elif record.tenant_id == tenant_id:
            record.state = pending.to_dict()
            record.updated_at = now
        await session.flush()

    async def clear(self, session: AsyncSession, key: uuid.UUID) -> None:
        await session.execute(delete(ConversationStateRecord).where(ConversationStateRecord.conversation_id == key))


pending_imports = PendingImportStore()
