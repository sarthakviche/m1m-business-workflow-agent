"""
M1M (Munim.ai) — Gemini AI Service
=====================================
Thin, reusable wrapper around the official ``google-genai`` Python SDK.

Usage
-----
    from app.services.gemini import get_gemini_client, generate_text

    client = get_gemini_client()          # cached singleton
    text   = generate_text("Say hello")   # simple one-shot helper

The service reads GEMINI_API_KEY exclusively from the application's
Settings object (pydantic-settings → .env file).

Security rules (non-negotiable):
  - The API key is NEVER hardcoded or printed/logged.
  - The key is accessed only via ``settings.gemini_api_key``.
  - Callers must not pass the raw key over the wire.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings

# ─── Default model ────────────────────────────────────────────────────────────
# Intent extraction is a small structured-output task, so the fast "lite" tier
# is the right fit. Measured 2026-11-16 on the classification prompt:
#   gemini-flash-lite-latest  ~1.2s, correct output
#   gemini-3.6-flash          504 DEADLINE_EXCEEDED after ~19s (every attempt)
# Override with GEMINI_MODEL without a code change if a model degrades.
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Hard ceiling for one AI call. Past this the rule-based parser answers instead,
# so a slow or overloaded model can never stall a chat turn. The SDK's own
# retries are disabled: a retry after a timeout only doubles the wait.
# The API rejects deadlines under 10s.
GEMINI_API_VERSION = os.environ.get("GEMINI_API_VERSION", "v1beta")
GEMINI_TIMEOUT_S = max(10.0, float(os.environ.get("GEMINI_TIMEOUT_S", "10")))


def request_options() -> types.HttpOptions:
    """HTTP options for every Gemini call: bounded timeout, no hidden retries."""
    return types.HttpOptions(
        # Pinned: newer SDK releases default to v1, which rejects these models with a 404.
        api_version=GEMINI_API_VERSION,
        timeout=int(GEMINI_TIMEOUT_S * 1000),
        retry_options=types.HttpRetryOptions(attempts=1),
    )


class GeminiKeyMissingError(RuntimeError):
    """Raised when GEMINI_API_KEY is not set in the environment."""


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """
    Return a cached Gemini SDK client initialised with the application's
    API key.

    Raises
    ------
    GeminiKeyMissingError
        If GEMINI_API_KEY is absent or empty in the environment.
    """
    settings = get_settings()
    api_key: Optional[str] = (settings.gemini_api_key or "").strip() or None

    if not api_key:
        raise GeminiKeyMissingError(
            "GEMINI_API_KEY is not configured.  "
            "Add it to your .env file (see .env.example)."
        )

    return genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version=GEMINI_API_VERSION))


def generate_text(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Send a plain-text prompt to Gemini and return the response text.

    Parameters
    ----------
    prompt:
        The user message / instruction to send.
    model:
        Gemini model name (defaults to ``DEFAULT_MODEL``).

    Returns
    -------
    str
        The model's text response (stripped of leading/trailing whitespace).

    Raises
    ------
    GeminiKeyMissingError
        If GEMINI_API_KEY is not configured.
    google.genai.errors.APIError
        If the Gemini API returns an error (propagated as-is).
    """
    client = get_gemini_client()
    response = client.models.generate_content(
        model=model, contents=prompt, config=types.GenerateContentConfig(http_options=request_options())
    )
    return response.text.strip()
