"""
Munim.ai — Errors Package
"""
from app.errors.categories import (
    MunimError,
    ValidationError,
    InjectionError,
    AuthorizationError,
    AuthenticationError,
    TenantAccessError,
    NotFoundError,
    InsufficientInformationError,
    InventoryError,
    BusinessRuleError,
    DuplicateDocumentError,
    IntegrationError,
    ModelError,
    ModelTimeoutError,
    RateLimitError,
    InternalError,
)

__all__ = [
    "MunimError",
    "ValidationError",
    "InjectionError",
    "AuthorizationError",
    "AuthenticationError",
    "TenantAccessError",
    "NotFoundError",
    "InsufficientInformationError",
    "InventoryError",
    "BusinessRuleError",
    "DuplicateDocumentError",
    "IntegrationError",
    "ModelError",
    "ModelTimeoutError",
    "RateLimitError",
    "InternalError",
]
