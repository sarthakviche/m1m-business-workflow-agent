"""
Munim.ai — Tenant Resolver
============================
Maps an authenticated API key to a business_id (UUID).

Security invariant:
    business_id ALWAYS comes from this server-side lookup.
    It is NEVER read from the request body, URL params, or LLM output.

Phase 1 implementation:
    Simple static API key → business_id map loaded from settings.
    In development mode, requests without an API key fall back to the
    single seeded dev tenant. This fallback is disabled in production.

Phase 2+ (planned):
    JWT validation with business_id in claims.
    Multi-tenant API key table in the database.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Dict

from app.config import get_settings
from app.errors.categories import AuthenticationError


class TenantResolver:
    """
    Resolves an API key to an authenticated business_id.

    In development mode:
        - Valid key → mapped business_id
        - Missing key → dev tenant fallback (SPRINT_TENANT_ID_DEFAULT)

    In production mode:
        - Valid key → mapped business_id
        - Missing/invalid key → AuthenticationError
    """

    def __init__(self, key_map: Dict[str, uuid.UUID], dev_tenant_id: uuid.UUID | None, is_dev: bool):
        self._key_map = key_map
        self._dev_tenant_id = dev_tenant_id
        self._is_dev = is_dev

    def resolve(self, api_key: str | None) -> uuid.UUID:
        """
        Resolve an API key to a business_id.

        Parameters
        ----------
        api_key : str | None
            Value from the X-API-Key request header. None if header is absent.

        Returns
        -------
        uuid.UUID
            The authenticated business_id for this key.

        Raises
        ------
        AuthenticationError
            If no valid key is provided in non-development mode.
        """
        if api_key:
            # Strip whitespace, lookup in map
            resolved = self._key_map.get(api_key.strip())
            if resolved:
                return resolved
            # Key provided but not recognized
            raise AuthenticationError(
                detail="Unrecognized API key.",
                user_message="Invalid API key. Please check your credentials.",
            )

        # No key provided
        if self._is_dev and self._dev_tenant_id is not None:
            # Development fallback — allows running without auth during local dev
            return self._dev_tenant_id

        # Production: reject unauthenticated requests
        raise AuthenticationError(
            detail="No API key provided and not in development mode.",
            user_message="Please sign in to continue.",
        )


@lru_cache(maxsize=1)
def get_tenant_resolver() -> TenantResolver:
    """
    Cached singleton TenantResolver built from application settings.

    Key map is loaded from MUNIM_API_KEYS env var (JSON format):
        MUNIM_API_KEYS={"key-abc-123": "uuid-...", "key-def-456": "uuid-..."}

    If MUNIM_API_KEYS is not set, only dev fallback is available.
    """
    settings = get_settings()
    is_dev = settings.is_development
    # The demo tenant only ever exists in development.
    dev_tenant_id = uuid.UUID(settings.effective_sprint_tenant_id) if is_dev else None

    # Load API key → tenant_id map from settings
    key_map: Dict[str, uuid.UUID] = {}
    raw_keys = settings.munim_api_keys
    if raw_keys:
        import json
        try:
            for k, v in json.loads(raw_keys).items():
                key_map[k] = uuid.UUID(v)
        except (ValueError, AttributeError) as exc:
            # Say what's wrong without echoing the secret values.
            raise ValueError("MUNIM_API_KEYS must be a JSON map of API key to tenant UUID") from exc

    return TenantResolver(key_map=key_map, dev_tenant_id=dev_tenant_id, is_dev=is_dev)
