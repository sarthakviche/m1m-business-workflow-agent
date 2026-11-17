"""
M1M (Munim.ai) — FastAPI Application Entry Point
==================================================
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Import all models so that SQLAlchemy registers them with Base.metadata.
# This is required for Alembic autogenerate to discover all tables.
import app.models  # noqa: F401

from app.api.v1.router import api_v1_router
from app.auth.dependencies import get_request_context
from app.api.v1.documents import router as documents_router
from app.channels.telegram.router import close_telegram_handler
from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.errors.categories import MunimError
from app.observability import RequestContextMiddleware, configure_logging, configure_sentry
from app.rate_limit import RateLimitMiddleware

settings = get_settings()
configure_logging(settings.log_level)
configure_sentry(settings.sentry_dsn, environment=settings.env)
logger = logging.getLogger(__name__)

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Refuse to start with an unsafe config rather than fail open in production.
    problems = settings.production_config_problems()
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
    yield
    await close_telegram_handler()


app = FastAPI(
    title="M1M — Munim.ai API",
    description="Business copilot for Indian SMEs: quotations, invoices and stock over web and chat.",
    version=APP_VERSION,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)


@app.exception_handler(MunimError)
async def munim_error_handler(_request: Request, exc: MunimError) -> JSONResponse:
    # Map domain errors raised outside the orchestrator (e.g. auth dependencies)
    # to their HTTP status. Only the user-safe message is exposed.
    return JSONResponse(
        status_code=exc.http_status,
        content={"error_code": exc.code, "message": exc.user_message},
    )


# The last middleware added runs first. CORS stays outermost so that even the
# error response from RequestContextMiddleware is readable by the browser.
app.add_middleware(RateLimitMiddleware, enabled=settings.rate_limit_enabled)
app.add_middleware(RequestContextMiddleware, hsts=not settings.is_development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization", "Content-Type", "Accept", "X-API-Key",
        "X-Conversation-Id", "X-Idempotency-Key", "X-Request-ID",
    ],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

# Register API routes
app.include_router(api_v1_router)

# Document serving — mounted at root so /documents/{tenant_id}/{doc_type}/{filename}
# matches the pdf_url returned by pdf_service.py (no /api/v1 prefix).
app.include_router(documents_router)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["system"])
async def health_check():
    """Liveness: the process is up. Deliberately doesn't touch the database."""
    return {"status": "ok", "version": APP_VERSION}


@app.api_route("/ready", methods=["GET", "HEAD"], tags=["system"])
async def readiness_check() -> JSONResponse:
    """Readiness: the database answers. Also what the uptime monitor pings."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("system.database_unavailable")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})


@app.get("/health/agent", tags=["system"], dependencies=[Depends(get_request_context)])
async def agent_health_check() -> JSONResponse:
    """
    Deep check for the chat agent, for use before a demo: database, the AI model
    (with real latency) and the parser on a known sentence. Makes one AI call,
    so it needs the same login as the API.
    """
    import asyncio
    import time

    from app.services.gemini import DEFAULT_MODEL, GEMINI_TIMEOUT_S
    from app.services.intent_classifier import classify_intent_sync

    checks: dict = {}

    started = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"ok": True, "ms": int((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        checks["database"] = {"ok": False, "error": type(exc).__name__}

    # classify_intent_sync falls back to rules on any AI failure, so the model is
    # judged on the rule-free answer: a correct customer AND item list.
    started = time.perf_counter()
    try:
        res = await asyncio.to_thread(classify_intent_sync, "Create invoice for Demo Health Check: 7 MS Hex Bolt")
        ms = int((time.perf_counter() - started) * 1000)
        parsed = res.intent == "invoice" and bool(res.line_items) and (res.line_items[0].quantity == 7)
        checks["ai_model"] = {
            "ok": parsed and ms < GEMINI_TIMEOUT_S * 1000,
            "model": DEFAULT_MODEL,
            "ms": ms,
            "slow": ms > 5000,
            "parsed_correctly": parsed,
        }
    except Exception as exc:
        checks["ai_model"] = {"ok": False, "model": DEFAULT_MODEL, "error": type(exc).__name__}

    healthy = all(c.get("ok") for c in checks.values())
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "ok" if healthy else "degraded", "checks": checks})
