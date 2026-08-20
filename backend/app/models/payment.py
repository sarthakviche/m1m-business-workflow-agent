"""
Payment model — records individual payment transactions against an invoice.

An invoice may receive partial payments before being fully paid.
The invoice's `status` field (unpaid → partially_paid → paid) is updated
by the payment agent based on cumulative payment amounts.
"""

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (
        CheckConstraint(
            "method IN ('upi','cash','bank_transfer')",
            name="ck_payment_method",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
