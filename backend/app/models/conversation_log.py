"""
ConversationLog model — append-only audit log of all agent interactions.

Both WhatsApp and web chat messages are stored here, giving a unified
conversation history that surfaces on both channels.

The log is written to at the end of every agent graph run (log_conversation node).
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from app.db.base import Base


class ConversationLog(Base):
    __tablename__ = "conversation_log"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('whatsapp','web')",
            name="ck_convlog_channel",
        ),
        CheckConstraint(
            "direction IN ('inbound','outbound')",
            name="ck_convlog_direction",
        ),
        # Composite index for efficient per-tenant timeline queries
        Index("idx_convlog_tenant_time", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(Text, nullable=False)      # 'whatsapp' | 'web'
    direction: Mapped[str] = mapped_column(Text, nullable=False)    # 'inbound' | 'outbound'
    raw_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_invoked: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
