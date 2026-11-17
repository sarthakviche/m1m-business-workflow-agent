"""
Munim.ai — Tool Schemas
=========================
Defines input/output schemas for all registered tools.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Standard output format for ALL tools.
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    confirmation_required: bool = False
    confirmation_message: Optional[str] = None


class BaseToolInput(BaseModel):
    """Base model for tool inputs."""
    pass
