"""
Munim.ai — Server-side conversation history
=============================================
Messaging channels have no client holding the transcript (unlike the web
app), so history is rebuilt from ``conversation_log`` per conversation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_log import ConversationLog

# Matches the orchestrator's 10-turn context window.
DEFAULT_HISTORY_MESSAGES = 20
# Older turns are a finished conversation: replaying them makes the agent
# resume requests the user has moved on from. Same window as the
# conversation state TTL.
DEFAULT_HISTORY_WINDOW = timedelta(minutes=30)


async def load_recent_history(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    limit: int = DEFAULT_HISTORY_MESSAGES,
    window: timedelta = DEFAULT_HISTORY_WINDOW,
) -> List[Dict[str, str]]:
    """Return up to ``limit`` messages from the last ``window``, oldest first, as {'role', 'content'} dicts."""
    since = datetime.now(timezone.utc) - window
    stmt = (
        select(ConversationLog.direction, ConversationLog.raw_message)
        .where(
            ConversationLog.tenant_id == tenant_id,
            ConversationLog.conversation_id == conversation_id,
            ConversationLog.created_at >= since,
        )
        # Both rows of a turn share created_at; 'outbound' > 'inbound' keeps
        # the reply after its message once the list is reversed.
        .order_by(ConversationLog.created_at.desc(), ConversationLog.direction.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"role": "user" if direction == "inbound" else "assistant", "content": text or ""}
        for direction, text in reversed(rows)
    ]
