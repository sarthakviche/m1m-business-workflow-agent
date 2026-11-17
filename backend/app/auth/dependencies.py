"""
Munim.ai — Auth FastAPI Dependencies
======================================
Every tenant-scoped endpoint gets its tenant from here, and only from here.

    Authorization: Bearer <login token>   → the user's business (the web app)
    X-API-Key: <key>                      → the key's business (server-to-server)
    neither, ENV=development only         → the demo tenant
    neither, otherwise                    → 401

Usage:
    @router.post("/chat")
    async def chat(context: RequestContext = Depends(get_request_context)):
        ...
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tenant_resolver import get_tenant_resolver
from app.auth.tokens import Principal, get_token_verifier
from app.db.session import get_db_session
from app.errors.categories import AuthenticationError, BusinessRequiredError
from app.models.app_user import AppUser
from app.orchestrator.context import RequestContext

_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> Principal | None:
    """The verified login, or None when no bearer token was sent. A bad token is always a 401."""
    if credentials is None:
        return None
    return await get_token_verifier().verify(credentials.credentials)


async def get_principal(
    principal: Annotated[Principal | None, Depends(get_optional_principal)] = None,
) -> Principal:
    if principal is None:
        raise AuthenticationError(detail="Login token required.", user_message="Please sign in to continue.")
    return principal


async def find_user(session: AsyncSession, principal: Principal) -> AppUser | None:
    result = await session.execute(select(AppUser).where(AppUser.auth_subject == principal.subject))
    return result.scalar_one_or_none()


async def get_request_context(
    principal: Annotated[Principal | None, Depends(get_optional_principal)] = None,
    api_key: Annotated[str | None, Depends(_api_key_scheme)] = None,
    session: AsyncSession = Depends(get_db_session),
    x_idempotency_key: Annotated[str | None, Header()] = None,
    x_conversation_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    """Resolve the caller's tenant server-side. It never comes from the body, URL or LLM output."""
    user_id: str | None = None
    role = "owner"

    if principal is not None:
        user = await find_user(session, principal)
        if user is None:
            raise BusinessRequiredError(detail=f"No business for subject {principal.subject}")
        business_id = user.tenant_id
        user_id = str(user.id)
        role = user.role
    else:
        business_id = get_tenant_resolver().resolve(api_key)

    conversation_id = uuid.uuid4()
    if x_conversation_id:
        try:
            conversation_id = uuid.UUID(x_conversation_id)
        except ValueError:
            pass

    return RequestContext(
        business_id=business_id,
        conversation_id=conversation_id,
        channel="web",
        run_id=uuid.uuid4(),
        user_id=user_id,
        idempotency_key=x_idempotency_key or str(uuid.uuid4()),
        role=role,
    )
