"""
M1M (Munim.ai) — API v1 Router
"""

from fastapi import APIRouter
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(chat_router)

# Document serving is mounted at /documents (no /api/v1 prefix)
# We include it on a root-level router registered on the app directly.
