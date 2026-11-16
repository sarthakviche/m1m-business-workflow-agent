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

from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_request_context
from app.db.session import get_db_session
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.orchestrator.context import RequestContext
from app.services.pdf_service import load_pdf

router = APIRouter(tags=["documents"])

# Where PDFs lived before moving into the database (matches pdf_service.py _DOCS_DIR).
_DOCS_ROOT = Path(__file__).resolve().parents[3] / "generated_docs"


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
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """Retrieve document history (quotations and invoices) for the authenticated tenant."""
    tenant_id = context.business_id

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
    response_class=Response,
    summary="Serve a generated PDF document",
    description=(
        "Streams a generated quotation or invoice PDF belonging to the caller's business. "
        "Only .pdf files are served; path traversal is rejected with 400."
    ),
)
async def serve_document(
    tenant_id: str,
    doc_type: str,
    filename: str,
    context: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Serve a stored PDF. Returns 404 for another business's document (never
    confirming that it exists) and for anything missing, 400 if it isn't a PDF.
    """
    if tenant_id != str(context.business_id):
        raise HTTPException(status_code=404, detail="Document not found.")

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are served.")

    content = await load_pdf(session, f"/documents/{tenant_id}/{doc_type}/{filename}", context.business_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{quote(filename)}"',
            "Cache-Control": "private, no-store",
        },
    )

