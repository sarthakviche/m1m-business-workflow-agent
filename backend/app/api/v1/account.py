"""
M1M (Munim.ai) — Account API
==============================
    GET  /api/v1/me         Who is signed in, and their business if they have one
    POST /api/v1/business   Create a business for a user who just signed up

A new login has no business, so these are the only two endpoints that don't
go through get_request_context's business lookup.
"""

from __future__ import annotations

import re
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.management import BusinessProfile, BusinessProfileUpdate, business_profile
from app.auth.dependencies import find_user, get_optional_principal, get_principal, get_request_context
from app.auth.tenant_resolver import get_tenant_resolver
from app.auth.tokens import Principal
from app.db.session import get_db_session
from app.errors.categories import BusinessRuleError, NotFoundError, ValidationError
from app.models.app_user import AppUser
from app.models.document import DocumentFile
from app.models.tenant import Tenant
from app.orchestrator.context import RequestContext

router = APIRouter(tags=["account"])

_LOGO_DOC_TYPE = "business_assets"
_LOGO_FILENAME = "logo"
_LOGO_MAX_BYTES = 1_024 * 1_024
_BRAND_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class MeResponse(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    business: Optional[BusinessProfile] = None


class BusinessCreate(BusinessProfileUpdate):
    business_name: str = Field(min_length=1, max_length=200)
    state: str = Field(min_length=2, max_length=60)


class BrandingUpdate(BaseModel):
    brand_color: Optional[str] = None

    @field_validator("brand_color")
    @classmethod
    def _validate_color(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        normalized = value.strip()
        if not _BRAND_COLOR_PATTERN.fullmatch(normalized):
            raise ValueError("Brand colour must look like #1A2B3C")
        return normalized.lower()


class BrandingResponse(BaseModel):
    brand_color: Optional[str]
    logo_url: Optional[str]


def _logo_media_type(content: bytes) -> Optional[str]:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


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


@router.get("/business/branding", response_model=BrandingResponse)
async def get_business_branding(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> BrandingResponse:
    tenant = await session.get(Tenant, context.business_id)
    if tenant is None:
        raise NotFoundError(detail=f"Tenant {context.business_id} not found", user_message="Business not found.")
    return BrandingResponse(brand_color=tenant.brand_color, logo_url=tenant.logo_url)


@router.patch("/business/branding", response_model=BrandingResponse)
async def update_business_branding(
    body: BrandingUpdate,
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> BrandingResponse:
    tenant = await session.get(Tenant, context.business_id)
    if tenant is None:
        raise NotFoundError(detail=f"Tenant {context.business_id} not found", user_message="Business not found.")
    tenant.brand_color = body.brand_color
    await session.commit()
    return BrandingResponse(brand_color=tenant.brand_color, logo_url=tenant.logo_url)


@router.post("/business/logo", response_model=BrandingResponse)
async def upload_business_logo(
    file: UploadFile = File(...),
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> BrandingResponse:
    content = await file.read(_LOGO_MAX_BYTES + 1)
    if len(content) > _LOGO_MAX_BYTES:
        raise ValidationError(
            detail=f"Logo upload exceeds {_LOGO_MAX_BYTES} bytes",
            user_message="Your logo must be 1 MB or smaller.",
        )
    if _logo_media_type(content) is None:
        raise ValidationError(
            detail="Unsupported logo file signature",
            user_message="Upload a PNG or JPEG logo.",
        )

    tenant = await session.get(Tenant, context.business_id)
    if tenant is None:
        raise NotFoundError(detail=f"Tenant {context.business_id} not found", user_message="Business not found.")
    logo = await session.get(DocumentFile, (context.business_id, _LOGO_DOC_TYPE, _LOGO_FILENAME))
    if logo is None:
        session.add(DocumentFile(
            tenant_id=context.business_id,
            doc_type=_LOGO_DOC_TYPE,
            filename=_LOGO_FILENAME,
            content=content,
        ))
    else:
        logo.content = content
    tenant.logo_url = "/api/v1/business/logo"
    await session.commit()
    return BrandingResponse(brand_color=tenant.brand_color, logo_url=tenant.logo_url)


@router.get("/business/logo")
async def get_business_logo(
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    logo = await session.get(DocumentFile, (context.business_id, _LOGO_DOC_TYPE, _LOGO_FILENAME))
    if logo is None:
        raise NotFoundError(detail="Business logo not found", user_message="No business logo has been uploaded.")
    media_type = _logo_media_type(logo.content)
    if media_type is None:
        raise NotFoundError(detail="Business logo has invalid signature", user_message="No business logo has been uploaded.")
    return Response(content=logo.content, media_type=media_type)
