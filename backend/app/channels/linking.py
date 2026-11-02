"""
Munim.ai — Channel account linking
====================================
Binds an external messaging account (Telegram user, later WhatsApp number)
to a tenant.

Flow:
    1. An authenticated caller (web app / ops CLI) creates a link code for
       their tenant. The plaintext code is returned once; only its SHA-256
       hash is stored.
    2. The user sends the code to the bot (``/start CODE`` or ``/link CODE``).
    3. The code is redeemed exactly once, before it expires, creating or
       re-pointing the ChannelIdentity.

Security invariant:
    The tenant for every channel message comes from ChannelIdentity, never
    from anything the user types.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import ChannelIdentity, ChannelLinkCode

Channel = Literal["telegram", "whatsapp"]

# No 0/O, 1/I/L: codes are typed by hand on a phone.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8


@dataclass(frozen=True)
class IssuedLinkCode:
    code: str
    expires_at: datetime


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def normalize_code(raw: str) -> str:
    return "".join(ch for ch in (raw or "").upper() if ch.isalnum())


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; treat them as UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def create_link_code(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    channel: Channel,
    ttl: timedelta,
) -> IssuedLinkCode:
    code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
    expires_at = datetime.now(timezone.utc) + ttl
    session.add(ChannelLinkCode(
        tenant_id=tenant_id,
        channel=channel,
        code_hash=_hash_code(code),
        expires_at=expires_at,
    ))
    await session.flush()
    return IssuedLinkCode(code=code, expires_at=expires_at)


async def redeem_link_code(
    session: AsyncSession,
    raw_code: str,
    *,
    channel: Channel,
    external_user_id: str,
    external_chat_id: str,
    display_name: Optional[str],
) -> Optional[ChannelIdentity]:
    """Consume a valid code and link the account. Returns None if the code is unusable."""
    code = normalize_code(raw_code)
    if len(code) != _CODE_LENGTH:
        return None

    result = await session.execute(
        select(ChannelLinkCode).where(ChannelLinkCode.code_hash == _hash_code(code)).with_for_update()
    )
    link_code = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if (
        link_code is None
        or link_code.channel != channel
        or link_code.used_at is not None
        or _as_utc(link_code.expires_at) <= now
    ):
        return None

    link_code.used_at = now
    identity = await get_identity(session, channel, external_user_id)
    if identity is None:
        identity = ChannelIdentity(
            tenant_id=link_code.tenant_id,
            channel=channel,
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            display_name=display_name,
        )
        session.add(identity)
    else:
        identity.tenant_id = link_code.tenant_id
        identity.external_chat_id = external_chat_id
        identity.display_name = display_name
    await session.flush()
    return identity


async def get_identity(session: AsyncSession, channel: Channel, external_user_id: str) -> Optional[ChannelIdentity]:
    result = await session.execute(
        select(ChannelIdentity).where(
            ChannelIdentity.channel == channel,
            ChannelIdentity.external_user_id == external_user_id,
        )
    )
    return result.scalar_one_or_none()


async def unlink(session: AsyncSession, channel: Channel, external_user_id: str) -> bool:
    result = await session.execute(
        delete(ChannelIdentity).where(
            ChannelIdentity.channel == channel,
            ChannelIdentity.external_user_id == external_user_id,
        )
    )
    return (result.rowcount or 0) > 0
