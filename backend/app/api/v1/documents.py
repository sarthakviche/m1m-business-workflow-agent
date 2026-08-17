"""
M1M (Munim.ai) — Document Serving Router
=========================================
Serves generated PDF documents (quotations and invoices) stored locally under
``generated_docs/{tenant_id}/{doc_type}/{filename}.pdf``.

Route: GET /documents/{tenant_id}/{doc_type}/{filename}

Security notes (Sprint 1):
  - Only PDF files are served (whitelist by extension).
  - Path traversal is prevented by resolving the final path and asserting it
    remains inside the ``generated_docs`` root.
  - In production (Sprint 2+) this should be replaced by pre-signed S3 URLs.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["documents"])

# Root of all generated documents (matches pdf_service.py _DOCS_DIR)
# Resolves to: <repo>/backend/generated_docs/
_DOCS_ROOT = Path(__file__).resolve().parents[3] / "generated_docs"


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
