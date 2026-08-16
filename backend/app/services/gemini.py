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

from functools import lru_cache
from typing import Optional

from google import genai

from app.config import get_settings

# ─── Default model ────────────────────────────────────────────────────────────
# gemini-3.6-flash: verified working for this API key (2026-08-16).
# gemini-flash-latest → 503 UNAVAILABLE; gemini-2.5-flash → 404 NOT_FOUND.
# Update this constant when a newer stable model is confirmed available.
DEFAULT_MODEL = "gemini-3.6-flash"


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

    return genai.Client(api_key=api_key)


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
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text.strip()
