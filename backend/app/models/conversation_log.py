"""SQLAlchemy ORM model: conversation_log"""
import uuid
from datetime import datetime
from sqlalchemy import text, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, TIMESTAMP
from app.db.session import Base


class ConversationLog(Base):
    __tablename__ = "conversation_log"
    __table_args__ = (
        CheckConstraint("channel IN ('whatsapp','web')", name="convlog_channel_check"),
        CheckConstraint("direction IN ('inbound','outbound')", name="convlog_direction_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("tenant.id", ondelete="CASCADE"),
                                                  nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    raw_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_invoked: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True),
                                                  server_default=text("now()"))
