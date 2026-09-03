"""SQLAlchemy ORM models: invoice, invoice_line"""

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Date,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP, Numeric

from app.db.session import Base


class Invoice(Base):
    __tablename__ = "invoice"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_invoice_tenant_number",
        ),
        CheckConstraint(
            "status IN ('unpaid','partially_paid','paid')",
            name="invoice_status_check",
        ),
        CheckConstraint(
            "tally_push_status IN ('not_applicable','pending','pushed')",
            name="invoice_tally_status_check",
        ),
    )

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

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer.id"),
        nullable=False,
    )

    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotation.id"),
        nullable=True,
    )

    invoice_number: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    subtotal: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        server_default="0",
        nullable=False,
    )

    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        server_default="0",
        nullable=False,
    )

    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        server_default="0",
        nullable=False,
    )

    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="unpaid",
    )

    due_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    pdf_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tally_push_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="not_applicable",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
    )


Index(
    "idx_invoice_due_date",
    Invoice.due_date,
)

Index(
    "idx_invoice_tenant_status",
    Invoice.tenant_id,
    Invoice.status,
)


class InvoiceLine(Base):
    __tablename__ = "invoice_line"

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

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("item.id"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    gst_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )