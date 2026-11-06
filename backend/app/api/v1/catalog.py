"""
M1M (Munim.ai) — Catalog import API
=====================================
    POST /api/v1/catalog/import/preview   Upload a price-list photo/PDF/CSV; returns rows to review (no writes)
    POST /api/v1/catalog/import           Save the reviewed rows (create or update items and stock)

Tenant comes from the authenticated RequestContext.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_request_context
from app.db.session import get_db_session
from app.errors.categories import ValidationError
from app.orchestrator.context import RequestContext
from app.services.catalog_import import (
    MAX_IMPORT_ROWS,
    MAX_UPLOAD_BYTES,
    CatalogImportRow,
    apply_catalog_import,
    extract_catalog,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


class PreviewRowOut(BaseModel):
    name: str
    unit_price: Optional[float]
    unit: str
    hsn_code: Optional[str]
    gst_rate_percent: Optional[float]
    quantity_available: Optional[float]
    issues: List[str]
    match: str
    existing_item_id: Optional[str]
    existing_unit_price: Optional[float]


class PreviewOut(BaseModel):
    rows: List[PreviewRowOut]
    notes: Optional[str]
    skipped: int


class ImportIn(BaseModel):
    items: List[CatalogImportRow] = Field(min_length=1, max_length=MAX_IMPORT_ROWS)


class ImportOut(BaseModel):
    created: int
    updated: int
    unchanged: int


def _float(value) -> Optional[float]:
    return float(value) if value is not None else None


@router.post("/import/preview", response_model=PreviewOut)
async def preview_catalog_import(
    file: UploadFile = File(...),
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> PreviewOut:
    # Read one byte past the limit so oversized uploads are rejected without buffering them whole.
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not file.content_type:
        raise ValidationError(detail="Upload without content type", user_message="Couldn't tell what kind of file that is.")
    preview = await extract_catalog(session, context.business_id, content, file.content_type)
    return PreviewOut(
        rows=[
            PreviewRowOut(
                name=r.name,
                unit_price=_float(r.unit_price),
                unit=r.unit,
                hsn_code=r.hsn_code,
                gst_rate_percent=_float(r.gst_rate_percent),
                quantity_available=_float(r.quantity_available),
                issues=r.issues,
                match=r.match,
                existing_item_id=str(r.existing_item_id) if r.existing_item_id else None,
                existing_unit_price=_float(r.existing_unit_price),
            )
            for r in preview.rows
        ],
        notes=preview.notes,
        skipped=preview.skipped,
    )


@router.post("/import", response_model=ImportOut)
async def commit_catalog_import(
    body: ImportIn,
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> ImportOut:
    result = await apply_catalog_import(session, context.business_id, body.items)
    await session.commit()
    return ImportOut(created=result.created, updated=result.updated, unchanged=result.unchanged)
