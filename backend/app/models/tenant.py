"""
Tenant model — root of the multi-tenant hierarchy.

Every other tenant-scoped table (customer, item, stock, etc.)
references tenant.id via a foreign key.

A tenant is created when a new user signs up and sets up their business.
RLS policies are planned as a second line of defence (docs/IMPLEMENTATION_PLAN.md).
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
    # Set when the owner finishes or skips first-run setup.
    onboarded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
