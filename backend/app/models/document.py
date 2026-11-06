"""
Durable document records.

DocumentSequence hands out document numbers without gaps or duplicates.
DocumentFile keeps the PDF exactly as issued, in the same transaction as its
invoice or quotation, so one can never exist without the other. Free hosts wipe
their local disk on every restart, so PDFs can't live there.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, LargeBinary, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentSequence(Base):
    __tablename__ = "document_sequence"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), primary_key=True,
    )
    # The number prefix, e.g. "INV-202611-".
    prefix: Mapped[str] = mapped_column(Text, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False)


class DocumentFile(Base):
    __tablename__ = "document_file"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), primary_key=True,
    )
    doc_type: Mapped[str] = mapped_column(Text, primary_key=True)  # "quotations" | "invoices"
    filename: Mapped[str] = mapped_column(Text, primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), nullable=False,
    )
