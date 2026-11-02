"""
ConversationStateRecord — persisted multi-turn state for an in-progress
request (e.g. "quotation for Ramesh" waiting for the item list).

Rows exist only while a workflow is waiting on the user; they are deleted when
the workflow completes or the user switches topic. Persisting this (instead of
keeping it in process memory) keeps multi-turn requests correct across server
restarts and multiple workers.
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConversationStateRecord(Base):
    __tablename__ = "conversation_state"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
