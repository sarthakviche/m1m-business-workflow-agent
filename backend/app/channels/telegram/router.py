"""
Munim.ai — Telegram HTTP endpoints
====================================
POST /api/v1/telegram/webhook     Telegram → us. Verified by the secret token
                                  Telegram echoes in a header; acknowledged
                                  immediately, processed in the background.
POST /api/v1/telegram/link-codes  Authenticated (X-API-Key). Issues a one-time
                                  code that links a Telegram chat to the
                                  caller's tenant.
"""

from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.chat import get_db_session
from app.auth.dependencies import get_request_context
from app.channels.linking import create_link_code
from app.channels.telegram.client import TelegramClient
from app.channels.telegram.handler import TelegramUpdateHandler
from app.channels.telegram.types import TelegramUpdate
from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.orchestrator.context import RequestContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@lru_cache(maxsize=1)
def get_telegram_handler() -> TelegramUpdateHandler:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram channel is not configured.")
    client = TelegramClient(settings.telegram_bot_token, base_url=settings.telegram_api_base_url)
    return TelegramUpdateHandler(client, AsyncSessionLocal)


async def close_telegram_handler() -> None:
    """Release the HTTP client on application shutdown, if one was created."""
    if get_telegram_handler.cache_info().currsize:
        await get_telegram_handler().client.aclose()
        get_telegram_handler.cache_clear()


def verify_webhook_secret(
    x_telegram_bot_api_secret_token: Annotated[Optional[str], Header()] = None,
) -> None:
    settings = get_settings()
    expected = settings.telegram_webhook_secret
    if not expected or not settings.telegram_bot_token:
        # Webhook mode is off until both values are configured.
        raise HTTPException(status_code=404, detail="Not Found")
    provided = x_telegram_bot_api_secret_token or ""
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid webhook secret.")


@router.post("/webhook", dependencies=[Depends(verify_webhook_secret)])
async def telegram_webhook(
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any] = Body(...),
    handler: TelegramUpdateHandler = Depends(get_telegram_handler),
) -> Dict[str, bool]:
    try:
        update = TelegramUpdate.model_validate(payload)
    except ValidationError:
        # Acknowledge anyway: a non-2xx makes Telegram redeliver the same bad payload.
        logger.warning("telegram.webhook.unparseable_update")
        return {"ok": True}
    background_tasks.add_task(handler.handle, update)
    return {"ok": True}


class LinkCodeResponse(BaseModel):
    code: str
    expires_at: datetime
    instructions: str


@router.post("/link-codes", response_model=LinkCodeResponse, status_code=201)
async def create_telegram_link_code(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> LinkCodeResponse:
    ttl = timedelta(minutes=get_settings().telegram_link_code_ttl_minutes)
    issued = await create_link_code(session, context.business_id, "telegram", ttl)
    return LinkCodeResponse(
        code=issued.code,
        expires_at=issued.expires_at,
        instructions=f"Open the Munim bot in Telegram and send: /link {issued.code}",
    )
