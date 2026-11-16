"""
Munim.ai — Logging and request handling
=========================================
Structured JSON logs carrying a request ID, baseline security headers, and a
last-resort handler so that an unexpected error is a safe JSON response with
CORS headers, never a stack trace or a browser "network error".
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("munim.http")

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_STANDARD_LOG_FIELDS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        entry.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_LOG_FIELDS})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # httpx logs full request URLs, and Telegram URLs contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def configure_sentry(dsn: str | None, *, environment: str) -> None:
    """Error tracking, on only when SENTRY_DSN is set. Logged errors become Sentry events."""
    if not (dsn or "").strip():
        return
    import sentry_sdk

    # send_default_pii=False keeps request bodies, cookies and user details out of Sentry.
    sentry_sdk.init(dsn=dsn, environment=environment, send_default_pii=False, traces_sample_rate=0)


class RequestContextMiddleware:
    """Pure ASGI middleware, so the request ID context also reaches background tasks."""

    def __init__(self, app, *, hsts: bool = False):
        self.app = app
        self.response_headers = dict(_SECURITY_HEADERS)
        if hsts:
            self.response_headers["Strict-Transport-Security"] = "max-age=31536000"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()
        response_started = False

        async def send_with_headers(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                for name, value in self.response_headers.items():
                    headers[name] = value
                logger.info("http.request", extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": message["status"],
                    "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                })
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            logger.exception("http.unhandled_error", extra={"method": scope["method"], "path": scope["path"]})
            if response_started:
                raise
            response = JSONResponse(status_code=500, content={
                "error_code": "internal_error",
                "message": "Something went wrong on our side. Please try again.",
                "request_id": request_id,
            })
            await response(scope, receive, send_with_headers)
        finally:
            request_id_var.reset(token)
