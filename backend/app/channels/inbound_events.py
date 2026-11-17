"""
Munim.ai — Inbound event deduplication
========================================
Messaging platforms redeliver webhooks they consider unacknowledged. Each
event is claimed once via a unique (channel, external_event_id) row before it
is processed, so a retry can never create a second quotation or invoice.

Delivery is therefore at-most-once: if processing crashes after the claim,
the event is not retried. For document-creating actions that is the safer
failure mode.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.channel import ChannelInboundEvent


async def claim_event(session_factory: async_sessionmaker[AsyncSession], channel: str, external_event_id: str) -> bool:
    """Return True if this call claimed the event, False if it was already seen."""
    async with session_factory() as session:
        session.add(ChannelInboundEvent(channel=channel, external_event_id=external_event_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return False
    return True
