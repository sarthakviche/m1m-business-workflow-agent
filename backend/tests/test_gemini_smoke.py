"""
Sprint 1 Step 2 — Gemini API Smoke Test
=========================================
Verifies end-to-end connectivity between the M1M backend and the
Google Gemini API.

What this test does
-------------------
1. Asserts that GEMINI_API_KEY is present in the application settings.
2. Creates the Gemini client via the reusable service layer.
3. Sends the prompt "Reply with exactly: M1M_GEMINI_OK" to Gemini.
4. Asserts that the response contains the sentinel string "M1M_GEMINI_OK".

Running
-------
From the ``backend/`` directory (with .venv activated):

    pytest tests/test_gemini_smoke.py -v

Or, to run only this test alongside the full suite:

    pytest -v

Environment
-----------
Requires GEMINI_API_KEY in the project-root .env file.
See .env.example for the expected variable name.
"""

import pytest

from app.config import get_settings
from app.services.gemini import (
    DEFAULT_MODEL,
    GeminiKeyMissingError,
    generate_text,
    get_gemini_client,
)

# ─── Sentinel that the model must echo back ────────────────────────────────────
_EXPECTED_SENTINEL = "M1M_GEMINI_OK"
_SMOKE_PROMPT = f"Reply with exactly: {_EXPECTED_SENTINEL}"


# ─── Test 1: API key is configured ────────────────────────────────────────────

def test_gemini_api_key_is_configured():
    """
    GEMINI_API_KEY must be present and non-empty in application settings.

    Fails with a clear message if the key is missing so the developer
    knows exactly what to fix.
    """
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    assert api_key, (
        "GEMINI_API_KEY is not set.  "
        "Add it to your .env file at the project root.  "
        "See .env.example for the variable name."
    )


# ─── Test 2: Gemini client can be created ─────────────────────────────────────

def test_gemini_client_creation():
    """
    get_gemini_client() must return a valid google.genai.Client without
    raising GeminiKeyMissingError.
    """
    try:
        client = get_gemini_client()
    except GeminiKeyMissingError as exc:
        pytest.fail(
            f"Could not create Gemini client — API key missing: {exc}"
        )

    # Basic sanity: the returned object should have a 'models' attribute
    assert hasattr(client, "models"), (
        "get_gemini_client() did not return a valid genai.Client instance."
    )


# ─── Test 3: Live API smoke test ───────────────────────────────────────────────

def test_gemini_smoke_response():
    """
    Send a controlled prompt to Gemini and assert the sentinel is present
    in the response.

    This test makes a real network call — it will fail if:
      - GEMINI_API_KEY is invalid / expired
      - The Gemini API is unreachable
      - The model returns an unexpected response
    """
    try:
        response_text = generate_text(_SMOKE_PROMPT, model=DEFAULT_MODEL)
    except GeminiKeyMissingError as exc:
        pytest.fail(f"Gemini key missing: {exc}")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"Gemini API call failed with {type(exc).__name__}: {exc}"
        )

    assert response_text, "Gemini returned an empty response."
    assert _EXPECTED_SENTINEL in response_text, (
        f"Expected sentinel '{_EXPECTED_SENTINEL}' not found in response.\n"
        f"Model used : {DEFAULT_MODEL}\n"
        f"Full response: {response_text!r}"
    )
