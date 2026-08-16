"""
M1M (Munim.ai) — Chat API Endpoint
====================================
Developer-facing endpoint to execute the LangGraph Agent workflow.

POST /api/v1/chat
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import agent_graph
from app.config import get_settings
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["chat"])


async def get_db_session():
    """FastAPI dependency yielding an async database session with auto-commit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural language business request")


class ChatResponse(BaseModel):
    response_text: str
    intent: Optional[str] = None
    document_type: Optional[str] = None
    document_id: Optional[str] = None
    document_number: Optional[str] = None
    pdf_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    Handle natural language quotation, invoice, and conversion requests
    via the unified LangGraph agent.
    """
    settings = get_settings()
    tenant_id = settings.effective_sprint_tenant_id

    initial_state = {
        "tenant_id": tenant_id,
        "user_id": None,
        "channel": "web",
        "raw_message": request.message,
    }

    config = {
        "configurable": {
            "session": session,
        }
    }

    final_state = await agent_graph.ainvoke(initial_state, config=config)

    attachments = final_state.get("response_attachments") or []
    pdf_url = attachments[0].get("url") if attachments else None

    return ChatResponse(
        response_text=final_state.get("response_text", ""),
        intent=final_state.get("detected_intent"),
        document_type=final_state.get("document_type"),
        document_id=final_state.get("document_id"),
        document_number=final_state.get("document_number"),
        pdf_url=pdf_url,
        data=final_state.get("data"),
    )
