"""
Munim.ai — Auth FastAPI Dependencies
======================================
Provides FastAPI dependency functions for request authentication
and tenant context resolution.

Usage:
    @router.post("/chat")
    async def chat(context: RequestContext = Depends(get_request_context)):
        ...

The dependency chain:
    get_request_context
        → _resolve_api_key        (reads X-API-Key header)
        → TenantResolver.resolve  (maps key → business_id, server-side)
        → RequestContext(...)     (creates context with run_id, permissions)
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import APIKeyHeader

from app.auth.tenant_resolver import get_tenant_resolver
from app.orchestrator.context import RequestContext


# FastAPI security scheme for X-API-Key header
# auto_error=False so we can handle missing key gracefully (dev fallback)
_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_request_context(
    api_key: Annotated[str | None, Depends(_api_key_scheme)] = None,
    x_idempotency_key: Annotated[str | None, Header()] = None,
    x_conversation_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    """
    FastAPI dependency that resolves the full RequestContext for a request.

    Resolves:
        - business_id from X-API-Key header (server-side, never from body)
        - conversation_id from X-Conversation-Id header (or new UUID)
        - idempotency_key from X-Idempotency-Key header (or new UUID)
        - run_id is always a fresh UUID per request

    In development mode, missing X-API-Key falls back to the dev tenant.
    In production, missing X-API-Key raises 401.
    """
    resolver = get_tenant_resolver()
    business_id: uuid.UUID = resolver.resolve(api_key)

    # Resolve or generate conversation_id
    if x_conversation_id:
        try:
            conversation_id = uuid.UUID(x_conversation_id)
        except ValueError:
            conversation_id = uuid.uuid4()
    else:
        conversation_id = uuid.uuid4()

    # Idempotency key for write operations
    idempotency_key = x_idempotency_key or str(uuid.uuid4())

    return RequestContext(
        business_id=business_id,
        conversation_id=conversation_id,
        channel="web",                  # channel is set by the specific adapter/endpoint
        run_id=uuid.uuid4(),
        user_id=None,                   # user_id resolution via JWT comes in Phase 2
        idempotency_key=idempotency_key,
        role="owner",                   # role resolution from JWT claims in Phase 2
    )
