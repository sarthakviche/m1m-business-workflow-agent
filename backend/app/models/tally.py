"""SQLAlchemy ORM models: tally_connection, external_id_map"""
import uuid
from datetime import datetime
from sqlalchemy import text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP
from app.db.session import Base


class TallyConnection(Base):
    __tablename__ = "tally_connection"
    __table_args__ = (
        CheckConstraint("status IN ('not_connected','connected')", name="tally_status_check"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="not_connected")
    mode: Mapped[str] = mapped_column(Text, nullable=False, server_default="read_only")
    last_synced_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class ExternalIdMap(Base):
    __tablename__ = "external_id_map"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False)
    internal_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    internal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    external_system: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
