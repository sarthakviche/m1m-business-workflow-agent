"""
TallyConnection and ExternalIdMap models.

Sprint 1 note: Tally integration is SIMULATED — no live write-back is built.
These tables exist so the schema supports Phase 2 Tally sync without changes.

TallyConnection: per-tenant Tally connection status (not_connected / connected).
ExternalIdMap: maps internal M1M entity IDs to Tally/external system IDs.

Per the TRD, all invoices ship with tally_push_status='not_applicable' in
Sprint 1. The UI action is disabled and labelled as such.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from app.db.base import Base


class TallyConnection(Base):
    __tablename__ = "tally_connection"
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_connected','connected')",
            name="ck_tally_status",
        ),
    )

    # tenant_id is both the PRIMARY KEY and the FK — one row per tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_connected")
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="read_only")
    last_synced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class ExternalIdMap(Base):
    __tablename__ = "external_id_map"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 'customer', 'item', 'invoice', etc.
    internal_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    internal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # 'tally', 'zoho', etc.
    external_system: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
