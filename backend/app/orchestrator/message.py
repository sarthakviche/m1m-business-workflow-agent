"""
Munim.ai — Normalized Message
==============================
Channel-agnostic representation of an inbound user message.

Every channel adapter (WhatsApp, Web, Voice) converts its native
message format into a NormalizedMessage before passing it to the
MunimOrchestrator. The orchestrator never imports channel-specific
libraries directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Literal


@dataclass
class NormalizedMessage:
    """
    Canonical message format consumed by the orchestrator.

    Attributes
    ----------
    raw_text : str
        The user's message, stripped of channel-specific markup.
    channel : str
        Source channel — 'web' | 'whatsapp' | 'telegram' | 'voice'.
    sender_id : str
        Channel-level user identifier (phone number, browser session ID, etc.).
        This is NOT the authenticated user_id — it is resolved separately.
    idempotency_key : str
        Unique key for this specific message delivery.
        Used to prevent duplicate processing on retry/re-delivery.
        WhatsApp: use the WhatsApp message ID.
        Web: use a client-generated UUID per submit.
    conversation_history : list[dict]
        Previous turns in this conversation, each with 'role' and 'content'.
        Provided by the client for stateless web sessions.
        Will be replaced by server-side state in Phase 3.
    metadata : dict
        Channel-specific extras (e.g. media attachments, location, timestamps).
    """

    raw_text: str
    channel: Literal["web", "whatsapp", "telegram", "voice"]
    sender_id: str
    idempotency_key: str
    conversation_history: list[dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_web(
        cls,
        message: str,
        conversation_history: list[dict],
        idempotency_key: str | None = None,
    ) -> "NormalizedMessage":
        """Convenience factory for web channel requests."""
        return cls(
            raw_text=message.strip(),
            channel="web",
            sender_id="web-user",          # will be replaced by auth in Phase 1+
            idempotency_key=idempotency_key or str(uuid.uuid4()),
            conversation_history=conversation_history,
        )

    @classmethod
    def from_whatsapp(
        cls,
        message: str,
        phone_number: str,
        whatsapp_message_id: str,
        metadata: dict | None = None,
    ) -> "NormalizedMessage":
        """Convenience factory for WhatsApp channel requests."""
        return cls(
            raw_text=message.strip(),
            channel="whatsapp",
            sender_id=phone_number,
            idempotency_key=whatsapp_message_id,
            metadata=metadata or {},
        )

    @classmethod
    def from_telegram(
        cls,
        message: str,
        telegram_user_id: str,
        update_id: int,
        conversation_history: list[dict],
    ) -> "NormalizedMessage":
        """Factory for Telegram updates. History is loaded server-side per chat."""
        return cls(
            raw_text=message.strip(),
            channel="telegram",
            sender_id=telegram_user_id,
            idempotency_key=f"telegram:{update_id}",
            conversation_history=conversation_history,
        )
