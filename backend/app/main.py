"""
main.py — FastAPI application entrypoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import (
    auth,
    onboarding,
    chat,
    documents,
    customers,
    items,
    dashboard,
    whatsapp_webhook,
    invoice,
    quotations,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import sys
    import subprocess
    try:
        import reportlab
    except ImportError:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "reportlab==4.2.5"], check=True)
        except Exception as e:
            print("Failed to auto-install reportlab:", e)
    yield


app = FastAPI(
    title="M1M (Munim.ai) API",
    description="WhatsApp + Web business copilot for Indian SMEs — MVP backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.env == "development" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler — return structured JSON error
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": str(exc) if settings.env == "development" else "Something went wrong. Please try again."}},
    )


# Mount routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(whatsapp_webhook.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(invoice.router, prefix="/invoices", tags=["invoices"])
app.include_router(quotations.router, prefix="/quotations", tags=["quotations"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.env}
