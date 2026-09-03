"""SQLAlchemy ORM model: item"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP, Numeric

from app.db.session import Base


class Item(Base):
    __tablename__ = "item"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    hsn_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    gst_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        Text,
        server_default="pcs",
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
    )


Index(
    "idx_item_tenant",
    Item.tenant_id,
)

Index(
    "idx_item_name_trgm",
    Item.name,
    postgresql_using="gin",
    postgresql_ops={"name": "gin_trgm_ops"},
)