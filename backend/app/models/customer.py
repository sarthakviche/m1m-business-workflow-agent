"""SQLAlchemy ORM model: customer"""
import uuid
from datetime import datetime
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP
from app.db.session import Base


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    gstin: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                  server_default=text("now()"))
