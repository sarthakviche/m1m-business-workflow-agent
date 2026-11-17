"""
Munim.ai — Base Tool Definition
=================================
Abstract base class for all tools in the registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.orchestrator.context import RequestContext
from app.tools.schemas import ToolResult
from app.errors.categories import AuthorizationError


class BaseTool(ABC):
    """
    Abstract base class for a Munim tool.

    Every tool must declare its properties and implement `execute`.
    The registry will enforce permissions before calling `execute`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (e.g., 'create_invoice')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description provided to the LLM."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Type[BaseModel]:
        """Pydantic model defining the expected input arguments."""
        pass

    @property
    @abstractmethod
    def required_permissions(self) -> list[str]:
        """List of permissions required to execute this tool."""
        pass

    @property
    @abstractmethod
    def risk_level(self) -> int:
        """
        0: Read-only
        1: Draft write (no external effects)
        2: External side effect (send message/email)
        3: Financial commitment (payment, discount)
        """
        pass

    @property
    def requires_confirmation(self) -> bool:
        """Returns True if this tool requires explicit user confirmation (risk_level >= 2)."""
        return self.risk_level >= 2

    async def _check_permissions(self, context: RequestContext) -> None:
        """Verify the caller has all required permissions."""
        for perm in self.required_permissions:
            if not context.has_permission(perm):
                raise AuthorizationError(
                    detail=f"Missing permission: {perm}",
                    user_message="You don't have permission to perform this action.",
                )

    async def invoke(
        self,
        args: dict[str, Any],
        context: RequestContext,
        session: AsyncSession,
    ) -> ToolResult:
        """
        Public entry point for the orchestrator.
        Validates input, checks permissions, then calls `execute()`.
        """
        await self._check_permissions(context)
        parsed_input = self.input_schema.model_validate(args)
        
        # In Phase 4, we will add idempotency wrapping here for write tools.
        
        return await self.execute(parsed_input, context, session)

    @abstractmethod
    async def execute(
        self,
        input_data: BaseModel,
        context: RequestContext,
        session: AsyncSession,
    ) -> ToolResult:
        """Core tool logic. Must be implemented by subclasses."""
        pass
