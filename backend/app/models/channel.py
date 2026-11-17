"""
Channel models — link external messaging accounts (Telegram today, WhatsApp
next) to a tenant, and deduplicate webhook deliveries.

  - ChannelIdentity:     one external account (e.g. a Telegram user) → tenant.
  - ChannelLinkCode:     single-use, short-lived code that creates an identity.
                         Only the SHA-256 hash of the code is stored.
  - ChannelInboundEvent: one row per processed inbound event (Telegram
                         update_id). The unique constraint makes redelivered
                         webhooks a no-op.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CHANNELS = "channel IN ('telegram','whatsapp')"


class ChannelIdentity(Base):
    __tablename__ = "channel_identity"
    __table_args__ = (
        CheckConstraint(_CHANNELS, name="ck_channel_identity_channel"),
        UniqueConstraint("channel", "external_user_id", name="uq_channel_identity_user"),
        Index("idx_channel_identity_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    external_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    external_chat_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), nullable=False
    )


class ChannelLinkCode(Base):
    __tablename__ = "channel_link_code"
    __table_args__ = (
        CheckConstraint(_CHANNELS, name="ck_channel_link_code_channel"),
        UniqueConstraint("code_hash", name="uq_channel_link_code_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), nullable=False
    )


class ChannelInboundEvent(Base):
    __tablename__ = "channel_inbound_event"
    __table_args__ = (
        CheckConstraint(_CHANNELS, name="ck_channel_inbound_event_channel"),
        UniqueConstraint("channel", "external_event_id", name="uq_channel_inbound_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    external_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
