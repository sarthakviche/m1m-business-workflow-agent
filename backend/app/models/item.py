"""
Item model — a product in the tenant's catalog.

Every item must have:
  - hsn_code: required for GST-compliant invoices
  - gst_rate_percent: used by the deterministic GST calculator
  - unit_price: base price before tax
  - unit: unit of measure (kg, pcs, mtr, etc.)

The GIN/trgm index (idx_item_name_trgm) for fuzzy name matching is
created in the Alembic migration (not here) because it requires pg_trgm.
"""

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import TIMESTAMP, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from app.db.base import Base


class Item(Base):
    __tablename__ = "item"
    __table_args__ = (
        Index("idx_item_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # HSN (Harmonised System of Nomenclature) code — required for invoices
    hsn_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    # gst_rate_percent: e.g. 5.00, 12.00, 18.00, 28.00
    gst_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    # unit_price: per-unit sale price in INR (before GST)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # unit: 'kg', 'pcs', 'mtr', 'box', 'ltr', etc.
    unit: Mapped[str] = mapped_column(Text, nullable=False, default="pcs")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
