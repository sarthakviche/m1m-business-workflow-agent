"""
M1M (Munim.ai) — FastAPI Application Entry Point
==================================================
Sprint 1 stub — minimal app with no routes yet.
Routes (chat, documents, customers, items, webhooks) will be added in Sprint 1 Steps 2+.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models so that SQLAlchemy registers them with Base.metadata.
# This is required for Alembic autogenerate to discover all tables.
import app.models  # noqa: F401

from app.api.v1.router import api_v1_router
from app.api.v1.documents import router as documents_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="M1M — Munim.ai API",
    description=(
        "Business copilot for Indian SMEs — "
        "Quotation, Invoice, Dues, and Stock via WhatsApp + Web."
    ),
    version="0.1.0-sprint1",
    docs_url="/docs" if settings.env == "development" else None,
    redoc_url="/redoc" if settings.env == "development" else None,
)

# CORS — allow the Vite dev server and preview server to call the API.
# Only localhost origins are listed; no wildcard is used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:4173",   # Vite preview server
        "http://127.0.0.1:4173",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# Register API routes
app.include_router(api_v1_router)

# Document serving — mounted at root so /documents/{tenant_id}/{doc_type}/{filename}
# matches the pdf_url returned by pdf_service.py (no /api/v1 prefix).
app.include_router(documents_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness check — returns OK if the server is running."""
    return {"status": "ok", "env": settings.env, "version": "0.1.0-sprint1"}

