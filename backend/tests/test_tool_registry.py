"""
Tests for Tool Registry and BaseTool (Phase 2)
"""

import pytest
from pydantic import BaseModel
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.registry import ToolRegistry
from app.tools.base import BaseTool
from app.tools.schemas import ToolResult
from app.orchestrator.context import RequestContext
from app.errors.categories import AuthorizationError, NotFoundError

import uuid


class DummyInput(BaseModel):
    name: str


class DummyReadTool(BaseTool):
    name = "dummy_read"
    description = "A dummy read tool"
    input_schema = DummyInput
    required_permissions = ["dummy:read"]
    risk_level = 0

    async def execute(self, input_data: DummyInput, context: RequestContext, session: AsyncSession) -> ToolResult:
        return ToolResult(success=True, data={"hello": input_data.name})


class DummyFinancialTool(BaseTool):
    name = "dummy_financial"
    description = "A dummy financial tool"
    input_schema = DummyInput
    required_permissions = ["dummy:write"]
    risk_level = 3

    async def execute(self, input_data: DummyInput, context: RequestContext, session: AsyncSession) -> ToolResult:
        return ToolResult(success=True)


@pytest.fixture
def empty_registry():
    return ToolRegistry()


def test_tool_registration(empty_registry):
    tool = DummyReadTool()
    empty_registry.register(tool)
    
    assert len(empty_registry.list_all()) == 1
    
    retrieved = empty_registry.get("dummy_read")
    assert retrieved is tool

    with pytest.raises(ValueError, match="already registered"):
        empty_registry.register(tool)


def test_tool_not_found(empty_registry):
    with pytest.raises(NotFoundError):
        empty_registry.get("nonexistent_tool")


def test_risk_levels():
    read_tool = DummyReadTool()
    assert not read_tool.requires_confirmation
    assert read_tool.risk_level == 0

    fin_tool = DummyFinancialTool()
    assert fin_tool.requires_confirmation
    assert fin_tool.risk_level == 3


@pytest.mark.asyncio
async def test_tool_authorization():
    tool = DummyReadTool()
    
    # Context with permission
    ctx_pass = RequestContext(
        business_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        channel="web",
        permissions={"dummy:read"}
    )
    
    # Context without permission
    ctx_fail = RequestContext(
        business_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        channel="web",
        permissions={"dummy:other"}
    )
    
    # Should pass
    result = await tool.invoke({"name": "world"}, ctx_pass, None)
    assert result.success
    assert result.data["hello"] == "world"

    # Should raise AuthorizationError
    with pytest.raises(AuthorizationError, match="Missing permission: dummy:read"):
        await tool.invoke({"name": "world"}, ctx_fail, None)

