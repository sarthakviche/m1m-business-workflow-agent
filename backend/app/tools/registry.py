"""
Munim.ai — Tool Registry
==========================
Maintains the catalog of available tools. The LLM can only invoke
tools that are explicitly registered here.
"""

from __future__ import annotations

from typing import Dict, Type

from app.tools.base import BaseTool
from app.errors.categories import NotFoundError


class ToolRegistry:
    """
    Registry of all available tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise NotFoundError(
                detail=f"Tool not found: {name}",
                user_message="I'm not sure how to do that.",
            )
        return tool
    
    def list_all(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

# Global registry singleton
registry = ToolRegistry()
