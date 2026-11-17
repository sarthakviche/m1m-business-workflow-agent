"""
Munim.ai — Request Context
===========================
Authenticated, tenant-scoped context for a single orchestrator request.

The business_id in RequestContext is ALWAYS resolved from server-side
authentication. It is never read from the request body, query params,
or LLM output.

Security invariant:
    context.business_id is the ONLY source of truth for tenant scoping
    in all downstream service and database calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RequestContext:
    """
    Fully resolved, authenticated request context.

    Created once per inbound message by the orchestrator after auth validation.
    Passed to every downstream service — services must NOT accept business_id
    from any other source.

    Attributes
    ----------
    business_id : uuid.UUID
        Tenant identifier. Resolved server-side from the auth token.
        NEVER from request body or LLM output.
    user_id : str | None
        Authenticated user within the business. None for unauthenticated
        channels in development mode.
    conversation_id : uuid.UUID
        Active conversation. Resolved or created by the orchestrator.
    channel : str
        Source channel — 'web' | 'whatsapp' | 'telegram' | 'voice'.
    run_id : uuid.UUID
        Correlation ID for this specific request. Used in logs and audit.
        Every log line for this request includes run_id.
    idempotency_key : str
        Forwarded from NormalizedMessage. Used for dedup in write operations.
    role : str
        Caller's role — 'owner' | 'staff' | 'viewer'. Default 'owner' for Phase 1.
    permissions : set[str]
        Explicit permission set for this caller.
        e.g. {'invoice:read', 'invoice:write', 'quotation:write'}
    """

    business_id: uuid.UUID
    conversation_id: uuid.UUID
    channel: Literal["web", "whatsapp", "telegram", "voice"]
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: str | None = None
    idempotency_key: str = ""
    role: str = "owner"
    permissions: set[str] = field(default_factory=lambda: {
        # Phase 1 default: owner has all permissions
        "invoice:read", "invoice:write",
        "quotation:read", "quotation:write",
        "catalog:read",
        "customer:read", "customer:write",
        "payment:read", "payment:write",
    })

    def has_permission(self, permission: str) -> bool:
        """Check if this context has a specific permission."""
        return permission in self.permissions

    def require_permission(self, permission: str) -> None:
        """Raise AuthorizationError if permission is missing."""
        from app.errors.categories import AuthorizationError
        if not self.has_permission(permission):
            raise AuthorizationError(
                f"Permission '{permission}' is required for this action.",
                user_message="You don't have permission to perform this action.",
            )
