"""SQLAlchemy ORM model: app_user"""
import uuid
from datetime import datetime
from sqlalchemy import text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP
from app.db.session import Base


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("role IN ('owner','staff','accountant')", name="app_user_role_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False, index=True)
    phone: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="owner")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                  server_default=text("now()"))
