"""
Stock model — tracks available quantity for each catalog item.

Design decisions:
  - item_id is both the PRIMARY KEY and the FK to item — enforces a strict
    1:1 relationship (one stock row per item, always).
  - Stock is decremented by the Invoice Agent when an invoice is created.
  - quantity_available uses NUMERIC(12,2) to handle fractional quantities
    (e.g., 12.5 kg of steel).
"""

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import TIMESTAMP, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from app.db.base import Base


class Stock(Base):
    __tablename__ = "stock"

    # item_id is the PRIMARY KEY — enforces one stock row per item
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity_available: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
    )
    # last_updated is refreshed whenever stock is adjusted
    last_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
