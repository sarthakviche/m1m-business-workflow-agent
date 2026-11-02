"""
Munim.ai — Create Quotation Tool
"""

from typing import List
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.tools.schemas import ToolResult
from app.orchestrator.context import RequestContext
from app.context_builder.builder import context_builder
from app.services.quotation_service import create_quotation


class LineItemInput(BaseModel):
    item_name: str
    quantity: float


class CreateQuotationInput(BaseModel):
    customer_name: str = Field(..., description="Name of the customer")
    line_items: List[LineItemInput] = Field(..., description="Items to include in the quotation")


class CreateQuotationTool(BaseTool):
    name = "create_quotation"
    description = "Create a new quotation for a customer with specific items and quantities."
    input_schema = CreateQuotationInput
    required_permissions = ["quotation:write"]
    risk_level = 1  # Draft write, no external side effects yet

    async def execute(
        self,
        input_data: CreateQuotationInput,
        context: RequestContext,
        session: AsyncSession,
    ) -> ToolResult:
        
        # 1. Build task context (resolves DB entities securely)
        customer, resolved_items = await context_builder.build_quotation_context(
            customer_name=input_data.customer_name,
            line_items=[i.model_dump() for i in input_data.line_items],
            business_id=context.business_id,
            session=session,
        )

        # 2. Execute deterministic business service
        data = await create_quotation(
            session=session,
            tenant_id=context.business_id,
            customer=customer,
            items_with_qty=resolved_items,
        )

        return ToolResult(
            success=True,
            data=data,
        )
