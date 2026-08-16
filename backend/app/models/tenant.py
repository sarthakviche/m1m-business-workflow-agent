"""
Tenant model — root of the multi-tenant hierarchy.

Every other tenant-scoped table (customer, item, stock, etc.)
references tenant.id via a foreign key.

Sprint 1 note: Only one test tenant is seeded. RLS (Row-Level Security)
policies are intentionally deferred to Sprint 2+ — see README for details.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    business_name: Mapped[str] = mapped_column(Text, nullable=False)
    # GSTIN: required before generating GST-compliant invoices.
    # Format: 2-digit state code + 10-char PAN + 1 entity number + Z + 1 checksum
    gstin: Mapped[str | None] = mapped_column(Text, nullable=True)
    # state is used in the GST calculator (CGST+SGST vs IGST)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
