"""
M1M (Munim.ai) — Chat API Endpoint
====================================
Developer-facing endpoint to execute the LangGraph Agent workflow.

POST /api/v1/chat
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Literal
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_db_session
from app.auth.dependencies import get_request_context
from app.orchestrator.context import RequestContext
from app.orchestrator.message import NormalizedMessage
from app.orchestrator.orchestrator import OrchestratorResult, get_orchestrator

logger = logging.getLogger(__name__)

# Backstop for a whole turn. AI calls already stop at GEMINI_TIMEOUT_S and fall
# back to rules, so this only fires on something unexpected (a hung database).
# It stays under the ~30s proxy limits of free hosting, so the user sees a
# clear message instead of a bare 502.
TURN_TIMEOUT_S = 25.0

router = APIRouter(tags=["chat"])


class ConversationMessage(BaseModel):
    """Message in conversation history."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural language business request")
    conversation_history: List[ConversationMessage] = Field(default_factory=list, description="Previous messages in this conversation")


class ChatResponse(BaseModel):
    response_text: str
    intent: Optional[str] = None
    document_type: Optional[str] = None
    document_id: Optional[str] = None
    document_number: Optional[str] = None
    pdf_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    run_id: Optional[uuid.UUID] = None
    success: bool = True
    error_code: Optional[str] = None


async def _run_turn(request: ChatRequest, context: RequestContext, session: AsyncSession, on_progress=None) -> ChatResponse:
    history_dicts = [{"role": m.role, "content": m.content} for m in request.conversation_history]
    message = NormalizedMessage.from_web(
        message=request.message,
        conversation_history=history_dicts,
        idempotency_key=context.idempotency_key,
    )
    try:
        result = await asyncio.wait_for(
            get_orchestrator().process(message, context, session, on_progress=on_progress),
            timeout=TURN_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.error("chat.turn_timeout", extra={"run_id": str(context.run_id)})
        result = OrchestratorResult(
            response_text="That took longer than expected, so I stopped. Nothing was saved. Please send it again.",
            run_id=context.run_id,
            success=False,
            error_code="timeout",
        )

    # Persist before responding, so a document that failed to save is never
    # reported. A failed run is undone in full: no stock change, no half-made invoice.
    if result.success:
        await session.commit()
    else:
        await session.rollback()

    return ChatResponse(
        response_text=result.response_text,
        intent=result.intent,
        document_type=result.document_type,
        document_id=result.document_id,
        document_number=result.document_number,
        pdf_url=result.pdf_url,
        data=result.data,
        run_id=result.run_id,
        success=result.success,
        error_code=result.error_code,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Handle quotation, invoice, conversion and catalog requests via the orchestrator."""
    return await _run_turn(request, context, session)


@router.post("/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    context: RequestContext = Depends(get_request_context),
) -> StreamingResponse:
    """
    Same turn as POST /chat, streamed as newline-delimited JSON so the UI can
    show what the agent is doing:

        {"type": "status", "stage": "understanding"}
        {"type": "status", "stage": "drafting_invoice"}
        {"type": "result", "response": {...ChatResponse...}}

    The turn owns its own database session: a request-scoped one may already
    be closed while the body is still streaming.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def run() -> None:
        try:
            async with AsyncSessionLocal() as session:
                response = await _run_turn(request, context, session, on_progress=lambda stage: queue.put_nowait(("status", stage)))
            queue.put_nowait(("result", response.model_dump(mode="json")))
        except Exception:
            logger.exception("chat.stream_failed", extra={"run_id": str(context.run_id)})
            queue.put_nowait(("result", ChatResponse(
                response_text="Something went wrong. Please try again.",
                run_id=context.run_id, success=False, error_code="internal_error",
            ).model_dump(mode="json")))

    async def events():
        task = asyncio.create_task(run())
        try:
            while True:
                kind, payload = await queue.get()
                if kind == "status":
                    yield json.dumps({"type": "status", "stage": payload}) + "\n"
                else:
                    yield json.dumps({"type": "result", "response": payload}) + "\n"
                    return
        finally:
            if not task.done():
                task.cancel()

    # X-Accel-Buffering stops proxies from holding the stream until it ends.
    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
