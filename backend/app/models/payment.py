"""SQLAlchemy ORM model: payment"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP, Numeric
from app.db.session import Base


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (
        CheckConstraint(
            "method IS NULL OR method IN ('upi','cash','bank_transfer')",
            name="payment_method_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                   ForeignKey("invoice.id", ondelete="CASCADE"),
                                                   nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                               server_default=text("now()"))
