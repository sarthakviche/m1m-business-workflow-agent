"""
Munim.ai — Per-IP rate limits
===============================
A simple in-memory sliding window, which is enough while the API runs as one
instance. It stops a single client hammering the expensive endpoints. Limits are
generous because many Indian mobile users share one IP address. Fair AI usage
between businesses is handled separately in app.services.ai_quota.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse

_WINDOW_SECONDS = 60

# (method or None for any, path prefix, requests per minute). The first match wins.
RULES = (
    ("POST", "/api/v1/catalog/import/preview", 20),
    ("POST", "/api/v1/chat", 60),
    ("POST", "/api/v1/business", 20),
    (None, "/api/v1/telegram/webhook", None),  # Telegram's servers, verified by a secret
    (None, "/api/", 600),
    (None, "/documents/", 300),
)


class RateLimitMiddleware:
    def __init__(self, app, *, enabled: bool = True, rules=RULES, clock=time.monotonic):
        self.app = app
        self.enabled = enabled
        self.rules = rules
        self.clock = clock
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.next_cleanup = 0.0

    def _rule_for(self, method: str, path: str):
        for rule_method, prefix, limit in self.rules:
            if path.startswith(prefix) and rule_method in (None, method):
                return prefix, limit
        return None, None

    def _cleanup(self, now: float) -> None:
        if now < self.next_cleanup:
            return
        self.next_cleanup = now + _WINDOW_SECONDS
        for key in [k for k, hits in self.hits.items() if not hits or now - hits[-1] > _WINDOW_SECONDS]:
            del self.hits[key]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.enabled or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        prefix, limit = self._rule_for(scope["method"], scope["path"])
        if limit is None:
            await self.app(scope, receive, send)
            return

        now = self.clock()
        self._cleanup(now)
        client = scope["client"][0] if scope.get("client") else "unknown"
        hits = self.hits[(client, prefix)]
        while hits and now - hits[0] > _WINDOW_SECONDS:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = max(1, int(_WINDOW_SECONDS - (now - hits[0])) + 1)
            response = JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"error_code": "rate_limit", "message": "Too many requests. Please wait a moment and try again."},
            )
            await response(scope, receive, send)
            return

        hits.append(now)
        await self.app(scope, receive, send)
