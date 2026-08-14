"""SQLAlchemy ORM models: quotation, quotation_line"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP, Numeric
from app.db.session import Base


class Quotation(Base):
    __tablename__ = "quotation"
    __table_args__ = (
        UniqueConstraint("tenant_id", "quotation_number", name="uq_quotation_tenant_number"),
        CheckConstraint("status IN ('draft','sent','converted')", name="quotation_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                    ForeignKey("customer.id"), nullable=False)
    quotation_number: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                  server_default=text("now()"))


class QuotationLine(Base):
    __tablename__ = "quotation_line"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False)
    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                     ForeignKey("quotation.id", ondelete="CASCADE"),
                                                     nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                ForeignKey("item.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
