"""
Munim.ai — Conversation State Store
===================================
Persists and retrieves multi-turn ConversationState in the
``conversation_state`` table, using the caller's session so state changes
commit or roll back together with the rest of the request.

State is only kept while a workflow is waiting on the user. Entries older than
the TTL are treated as abandoned and ignored, so a half-finished request from
yesterday can never be silently resumed today.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.state import ConversationState
from app.models.conversation_state import ConversationStateRecord

DEFAULT_STATE_TTL = timedelta(minutes=30)


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; treat them as UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class ConversationStore:
    def __init__(self, ttl: timedelta = DEFAULT_STATE_TTL):
        self._ttl = ttl

    async def get(
        self, conversation_id: uuid.UUID, business_id: uuid.UUID, session: AsyncSession
    ) -> Optional[ConversationState]:
        """Retrieve live state for a conversation if it belongs to the business."""
        record = await session.get(ConversationStateRecord, conversation_id)
        if record is None or record.tenant_id != business_id:
            return None
        if datetime.now(timezone.utc) - _as_utc(record.updated_at) > self._ttl:
            return None
        return ConversationState.from_dict(record.state)

    async def save(self, state: ConversationState, session: AsyncSession) -> None:
        """Insert or replace the conversation state."""
        now = datetime.now(timezone.utc)
        record = await session.get(ConversationStateRecord, state.conversation_id)
        if record is None:
            session.add(ConversationStateRecord(
                conversation_id=state.conversation_id,
                tenant_id=state.business_id,
                state=state.to_dict(),
                updated_at=now,
            ))
        elif record.tenant_id == state.business_id:
            record.state = state.to_dict()
            record.updated_at = now
        await session.flush()

    async def clear(self, conversation_id: uuid.UUID, session: AsyncSession) -> None:
        """Clear state when a workflow completes or the user changes topic."""
        await session.execute(
            delete(ConversationStateRecord).where(ConversationStateRecord.conversation_id == conversation_id)
        )


conversation_store = ConversationStore()
