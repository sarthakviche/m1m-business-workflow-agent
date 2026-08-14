"""SQLAlchemy ORM model: tenant"""
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP
from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    business_name: Mapped[str] = mapped_column(Text, nullable=False)
    gstin: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                  server_default=text("now()"))
