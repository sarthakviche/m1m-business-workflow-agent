"""
Munim.ai — Login token verification
=====================================
Verifies the JWTs issued by Supabase Auth. Passwords, resets and Google sign-in
live with Supabase; this module only proves who a request comes from.

The signing algorithm is never taken on trust from the token. HS256 is accepted
only when a shared secret is configured, and asymmetric tokens are only checked
against keys from the project's JWKS endpoint. That rules out the classic
algorithm-confusion and ``alg: none`` attacks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.config import get_settings
from app.errors.categories import AuthenticationError

_ASYMMETRIC_ALGORITHMS = ("ES256", "RS256", "EdDSA")
_CLOCK_SKEW_SECONDS = 30
_INVALID_TOKEN_MESSAGE = "Your session has expired. Please sign in again."


@dataclass(frozen=True)
class Principal:
    """A verified login. It may not have a business yet (mid-signup)."""
    subject: str
    email: str | None = None
    name: str | None = None


class TokenVerifier:
    def __init__(
        self,
        *,
        audience: str,
        issuer: str | None = None,
        hs256_secret: str | None = None,
        jwks_client: PyJWKClient | None = None,
    ):
        self._audience = audience
        self._issuer = issuer
        self._hs256_secret = hs256_secret
        self._jwks_client = jwks_client

    @property
    def enabled(self) -> bool:
        return bool(self._hs256_secret or self._jwks_client)

    async def verify(self, token: str) -> Principal:
        if not self.enabled:
            raise AuthenticationError(
                detail="Bearer token received but login verification is not configured.",
                user_message="Sign-in isn't available right now.",
            )
        try:
            algorithm = jwt.get_unverified_header(token).get("alg")
            if algorithm == "HS256" and self._hs256_secret:
                key = self._hs256_secret
            elif algorithm in _ASYMMETRIC_ALGORITHMS and self._jwks_client:
                # The first lookup for a key is a network call, so keep it off the event loop.
                key = (await asyncio.to_thread(self._jwks_client.get_signing_key_from_jwt, token)).key
            else:
                raise jwt.InvalidAlgorithmError(f"Algorithm not accepted: {algorithm}")

            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=_CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError(
                detail=f"Rejected login token: {type(exc).__name__}",
                user_message=_INVALID_TOKEN_MESSAGE,
            ) from exc

        if claims.get("is_anonymous"):
            raise AuthenticationError(detail="Anonymous session rejected.", user_message=_INVALID_TOKEN_MESSAGE)

        metadata = claims.get("user_metadata") or {}
        return Principal(
            subject=claims["sub"],
            email=claims.get("email"),
            name=metadata.get("full_name") or metadata.get("name"),
        )


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifier:
    settings = get_settings()
    base_url = (settings.supabase_url or "").strip().rstrip("/")
    return TokenVerifier(
        audience=settings.supabase_jwt_audience,
        issuer=f"{base_url}/auth/v1" if base_url else None,
        hs256_secret=(settings.supabase_jwt_secret or "").strip() or None,
        jwks_client=PyJWKClient(f"{base_url}/auth/v1/.well-known/jwks.json", cache_keys=True) if base_url else None,
    )
