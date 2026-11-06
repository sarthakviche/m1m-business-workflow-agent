"""
Munim.ai — AI usage limits
============================
All businesses share one Gemini key and its daily limit, so each gets a fair
share and there's a ceiling overall. Going over isn't an error: the assistant
falls back to its rule-based parser.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.upsert import upsert_insert
from app.models.ai_usage import AiUsage

logger = logging.getLogger(__name__)


async def reserve_ai_call(session: AsyncSession, tenant_id: uuid.UUID) -> bool:
    """
    Count one AI call if there's room, and return whether it may go ahead.

    This commits, which also returns the database connection to the small pool
    for the seconds the AI call takes. Call it before the request writes anything.
    """
    settings = get_settings()
    today = datetime.now(timezone.utc).date()

    used = (await session.execute(
        select(AiUsage.calls).where(AiUsage.tenant_id == tenant_id, AiUsage.usage_date == today)
    )).scalar_one_or_none() or 0
    total = (await session.execute(
        select(func.coalesce(func.sum(AiUsage.calls), 0)).where(AiUsage.usage_date == today)
    )).scalar_one()

    if used >= settings.ai_daily_limit_per_business or total >= settings.ai_daily_limit_total:
        logger.warning("ai.quota_reached", extra={
            "tenant_id": str(tenant_id), "business_calls": used, "total_calls": total,
        })
        await session.commit()
        return False

    statement = upsert_insert(session, AiUsage).values(tenant_id=tenant_id, usage_date=today, calls=1)
    await session.execute(statement.on_conflict_do_update(
        index_elements=["tenant_id", "usage_date"],
        set_={"calls": AiUsage.calls + 1},
    ))
    await session.commit()
    return True
