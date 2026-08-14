"""
main.py — FastAPI application entrypoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import auth, onboarding, chat, documents, customers, items, dashboard, whatsapp_webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to do yet (DB created via Alembic migrations)
    yield
    # Shutdown: nothing to clean up yet


app = FastAPI(
    title="M1M (Munim.ai) API",
    description="WhatsApp + Web business copilot for Indian SMEs — MVP backend",
    version="0.1.0",
    lifespan=lifespan,
    # In production, restrict docs to internal use
    docs_url="/docs" if settings.env == "development" else None,
    redoc_url=None,
)

# CORS — allow the frontend origin (set properly in production via env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global error handler — never leak stack traces to the client
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # TODO (Phase 11 hardening): structured JSON logging here
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Something went wrong. Please try again."}},
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


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.env}
