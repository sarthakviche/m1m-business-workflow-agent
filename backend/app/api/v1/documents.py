"""
M1M (Munim.ai) — Document Serving and History Router
=====================================================
Serves generated PDF documents (quotations and invoices) stored locally under
``generated_docs/{tenant_id}/{doc_type}/{filename}.pdf``, and provides
the document history listing endpoint for the active tenant.

Routes:
  - GET /documents/{tenant_id}/{doc_type}/{filename} (File serving)
  - GET /api/v1/documents (Document list / history)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.quotation import Quotation

router = APIRouter(tags=["documents"])

# Root of all generated documents (matches pdf_service.py _DOCS_DIR)
# Resolves to: <repo>/backend/generated_docs/
_DOCS_ROOT = Path(__file__).resolve().parents[3] / "generated_docs"


async def get_db_session():
    """FastAPI dependency yielding an async database session with auto-commit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Pydantic Models for Document History ─────────────────────────────────────

class DocumentItem(BaseModel):
    id: str
    document_type: str  # "quotation" | "invoice"
    document_number: str
    customer_name: str
    created_at: str
    total: float
    status: str
    pdf_url: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]


# ─── Document History Listing ──────────────────────────────────────────────────

@router.get(
    "/api/v1/documents",
    response_model=DocumentListResponse,
    summary="List generated documents for tenant",
    description="Returns all quotations and invoices for the active tenant, ordered by creation date descending.",
)
async def list_documents(
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """Retrieve document history (quotations and invoices) for the active tenant."""
    settings = get_settings()
    tenant_id = uuid.UUID(settings.effective_sprint_tenant_id)

    # 1. Fetch quotations with customer names
    q_stmt = (
        select(Quotation, Customer.name.label("customer_name"))
        .join(Customer, Quotation.customer_id == Customer.id)
        .where(Quotation.tenant_id == tenant_id)
        .order_by(Quotation.created_at.desc())
    )
    q_res = await session.execute(q_stmt)
    q_rows = q_res.all()

    # 2. Fetch invoices with customer names
    inv_stmt = (
        select(Invoice, Customer.name.label("customer_name"))
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.tenant_id == tenant_id)
        .order_by(Invoice.created_at.desc())
    )
    inv_res = await session.execute(inv_stmt)
    inv_rows = inv_res.all()

    docs: List[DocumentItem] = []

    for q, cust_name in q_rows:
        docs.append(
            DocumentItem(
                id=str(q.id),
                document_type="quotation",
                document_number=q.quotation_number,
                customer_name=cust_name,
                created_at=q.created_at.isoformat() if q.created_at else "",
                total=float(q.subtotal or 0),
                status=q.status,
                pdf_url=q.pdf_url,
            )
        )

    for inv, cust_name in inv_rows:
        docs.append(
            DocumentItem(
                id=str(inv.id),
                document_type="invoice",
                document_number=inv.invoice_number,
                customer_name=cust_name,
                created_at=inv.created_at.isoformat() if inv.created_at else "",
                total=float(inv.total_amount or 0),
                status=inv.status,
                pdf_url=inv.pdf_url,
            )
        )

    # Sort combined list by created_at descending
    docs.sort(key=lambda d: d.created_at, reverse=True)

    return DocumentListResponse(documents=docs)


# ─── PDF Serving ──────────────────────────────────────────────────────────────

@router.get(
    "/documents/{tenant_id}/{doc_type}/{filename}",
    response_class=FileResponse,
    summary="Serve a generated PDF document",
    description=(
        "Streams a generated quotation or invoice PDF for the given tenant. "
        "Only .pdf files are served; path traversal is rejected with 400."
    ),
)
async def serve_document(tenant_id: str, doc_type: str, filename: str) -> FileResponse:
    """
    Serve a generated PDF from ``generated_docs/{tenant_id}/{doc_type}/{filename}``.

    Returns 400 if the resolved path escapes the docs root or the extension is
    not ``.pdf``.  Returns 404 if the file does not exist.
    """
    # Whitelist extension
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are served.")

    target = (_DOCS_ROOT / tenant_id / doc_type / filename).resolve()

    # Guard against path traversal
    try:
        target.relative_to(_DOCS_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document path.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Document not found.")

    return FileResponse(
        path=str(target),
        media_type="application/pdf",
        filename=filename,
    )

