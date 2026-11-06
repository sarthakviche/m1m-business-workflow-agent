"""
Munim.ai — Structured Error Categories
========================================
All application errors inherit from MunimError.

Design principles:
- Every error has a machine-readable code safe for logging and metrics.
- Every error has a safe user_message that can be shown to the merchant.
  The user_message NEVER exposes internal details (stack traces, SQL, etc.).
- The log_context dict captures internal debug info for structured logging only.
- The LLM may explain errors in natural language but must not invent causes.
"""

from __future__ import annotations

from typing import Any, Dict


class MunimError(Exception):
    """Base class for all Munim application errors."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(
        self,
        detail: str = "",
        user_message: str = "Something went wrong. Please try again.",
        log_context: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.user_message = user_message
        self.log_context = log_context or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "user_message": self.user_message,
        }


# ── Input / Validation ────────────────────────────────────────────────────────

class ValidationError(MunimError):
    """Malformed request, oversized input, or failed schema validation."""
    code = "validation_error"
    http_status = 422

    def __init__(self, detail: str = "", user_message: str = "The request contains invalid data."):
        super().__init__(detail, user_message)


class InjectionError(ValidationError):
    """Detected prompt injection or malicious input pattern."""
    code = "injection_error"
    http_status = 400

    def __init__(self, detail: str = ""):
        super().__init__(
            detail,
            user_message="I'm not able to process that request.",
        )


# ── Authorization / Tenant ────────────────────────────────────────────────────

class AuthorizationError(MunimError):
    """Caller does not have the required permission."""
    code = "authorization_error"
    http_status = 403

    def __init__(self, detail: str = "", user_message: str = "You don't have permission to do that."):
        super().__init__(detail, user_message)


class BusinessRequiredError(AuthorizationError):
    """A signed-in user who hasn't created their business yet."""
    code = "business_required"

    def __init__(self, detail: str = ""):
        super().__init__(detail, user_message="Please set up your business first.")


class AuthenticationError(MunimError):
    """No valid credentials provided."""
    code = "authentication_error"
    http_status = 401

    def __init__(self, detail: str = "", user_message: str = "Authentication required."):
        super().__init__(detail, user_message)


class TenantAccessError(MunimError):
    """Attempted to access another tenant's data."""
    code = "tenant_access_error"
    http_status = 403

    def __init__(self, detail: str = ""):
        super().__init__(
            detail,
            user_message="You don't have access to that resource.",
        )


# ── Not Found ─────────────────────────────────────────────────────────────────

class NotFoundError(MunimError):
    """Requested resource does not exist or belongs to another tenant."""
    code = "not_found"
    http_status = 404

    def __init__(self, detail: str = "", user_message: str = "The requested item was not found."):
        super().__init__(detail, user_message)


# ── Conversation / Information ─────────────────────────────────────────────────

class InsufficientInformationError(MunimError):
    """
    The request cannot be completed without more information from the user.
    Not an error per se — used to trigger the clarification flow.
    """
    code = "insufficient_information"
    http_status = 200     # not an HTTP error — part of normal clarification flow

    def __init__(self, detail: str = "", user_message: str = "I need a bit more information to proceed."):
        super().__init__(detail, user_message)


# ── Business Rules ─────────────────────────────────────────────────────────────

class InventoryError(MunimError):
    """Stock is insufficient or inventory operation failed."""
    code = "inventory_error"
    http_status = 409

    def __init__(self, detail: str = "", user_message: str = "Insufficient stock for this request."):
        super().__init__(detail, user_message)


class BusinessRuleError(MunimError):
    """A business rule was violated (e.g. duplicate invoice, invalid state transition)."""
    code = "business_rule_error"
    http_status = 409

    def __init__(self, detail: str = "", user_message: str = "This action cannot be completed due to a business rule."):
        super().__init__(detail, user_message)


class DuplicateDocumentError(BusinessRuleError):
    """Document already exists (idempotency replay or true duplicate)."""
    code = "duplicate_document"

    def __init__(self, detail: str = "", user_message: str = "This document has already been created."):
        MunimError.__init__(self, detail, user_message)


# ── External Integrations ──────────────────────────────────────────────────────

class IntegrationError(MunimError):
    """External service (WhatsApp, Tally, Google Sheets) call failed."""
    code = "integration_error"
    http_status = 502

    def __init__(self, detail: str = "", user_message: str = "An external service is temporarily unavailable. Please try again."):
        super().__init__(detail, user_message)


# ── AI / Model ────────────────────────────────────────────────────────────────

class ModelError(MunimError):
    """LLM call failed or returned unparseable output."""
    code = "model_error"
    http_status = 503

    def __init__(self, detail: str = "", user_message: str = "I'm having trouble understanding that right now. Please try again."):
        super().__init__(detail, user_message)


class ModelTimeoutError(ModelError):
    """LLM call timed out."""
    code = "model_timeout"

    def __init__(self, detail: str = ""):
        super().__init__(
            detail,
            user_message="The AI took too long to respond. Please try again.",
        )


# ── Infrastructure ─────────────────────────────────────────────────────────────

class RateLimitError(MunimError):
    """Request rate limit exceeded."""
    code = "rate_limit"
    http_status = 429

    def __init__(self, detail: str = "", user_message: str = "Too many requests. Please wait a moment and try again."):
        super().__init__(detail, user_message)


class InternalError(MunimError):
    """Unexpected internal error. Should not happen in normal operation."""
    code = "internal_error"
    http_status = 500

    def __init__(self, detail: str = "", user_message: str = "Something went wrong on our end. Please try again."):
        super().__init__(detail, user_message)
