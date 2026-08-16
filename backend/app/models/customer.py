"""
Customer model — a business's customer.

The `state` field is critical for the GST calculator:
  - If customer.state == tenant.state → CGST + SGST (intra-state)
  - If customer.state != tenant.state → IGST (inter-state)

The GIN/trgm index (idx_customer_name_trgm) for fuzzy name matching is
created in the Alembic migration (not here) because it requires the
pg_trgm extension to be installed first.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        Index("idx_customer_tenant", "tenant_id"),
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
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    # GSTIN of the customer (used for B2B invoice compliance)
    gstin: Mapped[str | None] = mapped_column(Text, nullable=True)
    # state: determines intra-state vs inter-state GST routing
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
