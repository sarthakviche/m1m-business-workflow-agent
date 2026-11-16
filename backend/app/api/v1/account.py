"""
M1M (Munim.ai) — Account API
==============================
    GET  /api/v1/me         Who is signed in, and their business if they have one
    POST /api/v1/business   Create a business for a user who just signed up

A new login has no business, so these are the only two endpoints that don't
go through get_request_context's business lookup.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.management import BusinessProfile, BusinessProfileUpdate, business_profile
from app.auth.dependencies import find_user, get_optional_principal, get_principal
from app.auth.tenant_resolver import get_tenant_resolver
from app.auth.tokens import Principal
from app.db.session import get_db_session
from app.errors.categories import BusinessRuleError
from app.models.app_user import AppUser
from app.models.tenant import Tenant

router = APIRouter(tags=["account"])


class MeResponse(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    business: Optional[BusinessProfile] = None


class BusinessCreate(BusinessProfileUpdate):
    business_name: str = Field(min_length=1, max_length=200)
    state: str = Field(min_length=2, max_length=60)


@router.get("/me", response_model=MeResponse)
async def get_me(
    principal: Annotated[Optional[Principal], Depends(get_optional_principal)] = None,
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    if principal is None:
        # No login: only the development demo tenant can answer; otherwise this is a 401.
        tenant = await session.get(Tenant, get_tenant_resolver().resolve(None))
        return MeResponse(role="owner", business=business_profile(tenant) if tenant else None)

    user = await find_user(session, principal)
    if user is None:
        return MeResponse(email=principal.email, name=principal.name)
    tenant = await session.get(Tenant, user.tenant_id)
    return MeResponse(
        email=principal.email or user.email,
        name=user.name or principal.name,
        role=user.role,
        business=business_profile(tenant) if tenant else None,
    )


@router.post("/business", response_model=BusinessProfile, status_code=201)
async def create_business(
    body: BusinessCreate,
    principal: Annotated[Principal, Depends(get_principal)],
    session: AsyncSession = Depends(get_db_session),
) -> BusinessProfile:
    already_exists = BusinessRuleError(
        f"Subject {principal.subject} already has a business",
        user_message="You already have a business on this account.",
    )
    if await find_user(session, principal) is not None:
        raise already_exists

    tenant = Tenant(
        business_name=body.business_name,
        state=body.state,
        gstin=body.gstin or None,
        address=body.address or None,
    )
    session.add(tenant)
    await session.flush()
    session.add(AppUser(
        tenant_id=tenant.id,
        auth_subject=principal.subject,
        email=principal.email,
        name=principal.name,
        role="owner",
    ))
    try:
        await session.commit()
    except IntegrityError:
        # A double-submitted signup form: the unique auth_subject means only one wins.
        await session.rollback()
        raise already_exists
    return business_profile(tenant)
