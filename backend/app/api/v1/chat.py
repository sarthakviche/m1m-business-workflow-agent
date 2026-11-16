"""
M1M (Munim.ai) — Chat API Endpoint
====================================
Developer-facing endpoint to execute the LangGraph Agent workflow.

POST /api/v1/chat
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.auth.dependencies import get_request_context
from app.orchestrator.context import RequestContext
from app.orchestrator.message import NormalizedMessage
from app.orchestrator.orchestrator import get_orchestrator

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


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Handle natural language quotation, invoice, and conversion requests
    via the unified MunimOrchestrator.
    """
    # 1. Normalize the inbound message from the web channel
    history_dicts = [{"role": m.role, "content": m.content} for m in request.conversation_history]
    message = NormalizedMessage.from_web(
        message=request.message,
        conversation_history=history_dicts,
        idempotency_key=context.idempotency_key,
    )

    # 2. Process through the central orchestrator
    orchestrator = get_orchestrator()
    result = await orchestrator.process(message, context, session)

    # 3. Persist before responding, so a document that failed to save is never
    # reported. A failed run is undone in full: no stock change, no half-made invoice.
    if result.success:
        await session.commit()
    else:
        await session.rollback()

    # 4. Return the standard response
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
