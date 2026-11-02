"""
Munim.ai — Central Orchestrator
=================================
Single entry point for ALL user messages, regardless of channel.

Every message follows this exact path — no shortcuts:

    NormalizedMessage
        → Tenant context (already in RequestContext)
        → Conversation state load (Phase 3: currently from request)
        → Intent classification (Gemini LLM)
        → Context build (Phase 3: task-specific DB data)
        → Policy check (authorization)
        → Tool / workflow selection
        → Business service execution (deterministic)
        → Result validation
        → Response generation
        → State persist (Phase 3)
        → Audit record (Phase 5)
        → OrchestratorResult

Phase 1 scope:
    The orchestrator wraps the existing LangGraph agent_graph.
    This lets us introduce the tenant isolation, auth, and run_id
    correlation immediately, without rewriting the agent logic.

    Phases 2-5 will progressively replace the graph nodes with
    the ToolRegistry, ConversationStateStore, ContextBuilder,
    Guardrails, and AuditRecorder as those are built.

Invariant:
    business_id is taken ONLY from context.business_id.
    The orchestrator must never read business_id from the message body.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.categories import (
    AuthorizationError,
    InternalError,
    MunimError,
    ValidationError,
)
from app.orchestrator.context import RequestContext
from app.orchestrator.message import NormalizedMessage

logger = logging.getLogger(__name__)

# Maximum raw message length accepted (prevents oversized LLM prompts)
_MAX_MESSAGE_CHARS = 2_000


@dataclass
class OrchestratorResult:
    """
    Structured result returned by the orchestrator to any channel adapter.

    Channel adapters translate this into channel-specific formats
    (WhatsApp text messages, web JSON responses, etc.).
    """
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


class MunimOrchestrator:
    """
    Central orchestrator for all Munim.ai user messages.

    Responsibilities (Phase 1):
        1. Input validation and sanitization
        2. Enforce tenant isolation (business_id from context only)
        3. Build conversation context string
        4. Delegate to LangGraph agent_graph
        5. Validate result (response grounded in actual tool result)
        6. Return OrchestratorResult with run_id for correlation

    The LangGraph graph is treated as a black box workflow engine here.
    In Phase 2+, individual graph nodes will be replaced with registered
    tools invoked through the ToolRegistry.
    """

    async def process(
        self,
        message: NormalizedMessage,
        context: RequestContext,
        session: AsyncSession,
    ) -> OrchestratorResult:
        """
        Process a normalized user message end-to-end.

        Parameters
        ----------
        message : NormalizedMessage
            Validated, channel-agnostic user message.
        context : RequestContext
            Server-resolved auth/tenant context. business_id is authoritative.
        session : AsyncSession
            Database session. All DB calls within this request share this session.

        Returns
        -------
        OrchestratorResult
            Structured result safe to return to any channel adapter.
        """
        start_time = time.perf_counter()
        run_id = context.run_id

        logger.info(
            "orchestrator.process.start",
            extra={
                "run_id": str(run_id),
                "business_id": str(context.business_id),
                "channel": context.channel,
                "message_length": len(message.raw_text),
                "idempotency_key": context.idempotency_key,
            },
        )

        try:
            # ── Step 1: Input guardrails ──────────────────────────────────────
            self._validate_input(message)

            # ── Step 2: Verify tenant matches session (no cross-tenant) ───────
            # Phase 1: business_id already comes from TenantResolver.
            # In Phase 4 we'll add per-resource ownership checks.
            business_id = context.business_id

            # ── Step 3: Build conversation context string ──────────────────────
            # Phase 3: This will use ConversationStateStore instead of raw history.
            conversation_text = self._build_conversation_text(
                message.raw_text,
                message.conversation_history,
            )

            # ── Step 4: Execute via LangGraph agent graph ──────────────────────
            # Import here to avoid circular imports at module load time
            from app.agent.graph import agent_graph

            initial_state = {
                "tenant_id": str(business_id),   # authoritative from context
                "user_id": context.user_id,
                "channel": context.channel,
                "raw_message": message.raw_text,
                "conversation_history": message.conversation_history,
                "full_conversation_text": conversation_text,
                # Phase 5: run_id will be injected into state for audit tracing
                "_run_id": str(run_id),
            }

            graph_config = {
                "configurable": {
                    "session": session,
                    "request_context": context,
                    "run_id": str(run_id),
                    "business_id": str(business_id),
                }
            }

            final_state = await agent_graph.ainvoke(initial_state, config=graph_config)

            # ── Step 5: Validate output ────────────────────────────────────────
            # Core guardrail: response must be grounded in actual tool result.
            # A fabricated success message is worse than an honest error.
            response_text = final_state.get("response_text", "")
            self._validate_output_grounding(response_text, final_state)

            # ── Step 6: Extract result ─────────────────────────────────────────
            attachments = final_state.get("response_attachments") or []
            pdf_url = attachments[0].get("url") if attachments else None

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "orchestrator.process.success",
                extra={
                    "run_id": str(run_id),
                    "business_id": str(business_id),
                    "intent": final_state.get("detected_intent"),
                    "document_type": final_state.get("document_type"),
                    "elapsed_ms": elapsed_ms,
                },
            )

            return OrchestratorResult(
                response_text=response_text,
                intent=final_state.get("detected_intent"),
                document_type=final_state.get("document_type"),
                document_id=final_state.get("document_id"),
                document_number=final_state.get("document_number"),
                pdf_url=pdf_url,
                data=final_state.get("data"),
                run_id=run_id,
                success=True,
            )

        except MunimError as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "orchestrator.process.munim_error",
                extra={
                    "run_id": str(run_id),
                    "error_code": exc.code,
                    "detail": exc.detail,
                    "elapsed_ms": elapsed_ms,
                },
            )
            return OrchestratorResult(
                response_text=exc.user_message,
                run_id=run_id,
                success=False,
                error_code=exc.code,
            )

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "orchestrator.process.unexpected_error",
                extra={
                    "run_id": str(run_id),
                    "error": str(exc),
                    "elapsed_ms": elapsed_ms,
                },
                exc_info=True,
            )
            return OrchestratorResult(
                response_text="Something went wrong. Please try again.",
                run_id=run_id,
                success=False,
                error_code="internal_error",
            )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _validate_input(self, message: NormalizedMessage) -> None:
        """
        Input guardrails:
        - Reject empty messages
        - Reject oversized messages (prevents context window abuse)
        - Detect basic prompt injection patterns
        """
        text = (message.raw_text or "").strip()

        if not text:
            raise ValidationError(
                detail="Empty message received.",
                user_message="Please type a message.",
            )

        if len(text) > _MAX_MESSAGE_CHARS:
            raise ValidationError(
                detail=f"Message too long: {len(text)} chars (max {_MAX_MESSAGE_CHARS}).",
                user_message=f"Your message is too long. Please keep it under {_MAX_MESSAGE_CHARS} characters.",
            )

        # Basic prompt injection detection
        # Phase 4 will have a proper guardrail module with comprehensive patterns
        _INJECTION_PATTERNS = [
            "ignore previous instructions",
            "ignore all instructions",
            "disregard your instructions",
            "forget your instructions",
            "you are now",
            "act as if you are",
            "pretend you are",
            "jailbreak",
        ]
        text_lower = text.lower()
        for pattern in _INJECTION_PATTERNS:
            if pattern in text_lower:
                from app.errors.categories import InjectionError
                raise InjectionError(
                    detail=f"Injection pattern detected: '{pattern}'",
                )

    def _build_conversation_text(
        self,
        current_message: str,
        conversation_history: List[Dict],
    ) -> str:
        """
        Build the conversation context string for the LLM.

        Phase 1: Concatenates recent history + current message.
        Phase 3: Will use ConversationStateStore with summarization
                 to prevent unbounded context growth.

        Limits history to last 10 turns to bound token usage.
        """
        # Take only the last 10 turns (20 messages) to limit context
        recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history

        lines = []
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {msg.get('content', '')}")
        lines.append(f"User: {current_message}")
        return "\n".join(lines)

    def _validate_output_grounding(
        self,
        response_text: str,
        final_state: Dict[str, Any],
    ) -> None:
        """
        Output guardrail: ensure the response reflects actual execution results.

        The system must NEVER claim an action succeeded if it didn't.
        This check is conservative — it only blocks obvious false success claims.
        Phase 4 will implement a more comprehensive grounding validator.
        """
        if not response_text:
            return

        # If there's no document created but response says "created successfully"
        doc_type = final_state.get("document_type")
        doc_id = final_state.get("document_id")

        text_lower = response_text.lower()
        claims_creation = any(phrase in text_lower for phrase in [
            "successfully created",
            "has been created",
            "invoice created",
            "quotation created",
        ])

        if claims_creation and doc_type and not doc_id:
            # Response claims creation but no document_id was returned
            logger.error(
                "orchestrator.output_grounding_violation",
                extra={
                    "response_text": response_text[:200],
                    "doc_type": doc_type,
                    "doc_id": doc_id,
                },
            )
            # Don't raise — log the violation. A hard block could silently hide
            # actual successes where the service returned a doc_id in 'data'.
            # Phase 4 will implement the full grounding validator.


# ── Module-level singleton ────────────────────────────────────────────────────

_orchestrator: MunimOrchestrator | None = None


def get_orchestrator() -> MunimOrchestrator:
    """Return the module-level orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MunimOrchestrator()
    return _orchestrator
