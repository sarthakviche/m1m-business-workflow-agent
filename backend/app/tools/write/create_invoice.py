"""
Munim.ai — Create Invoice Tool
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.tools.schemas import ToolResult
from app.orchestrator.context import RequestContext
from app.context_builder.builder import context_builder
from app.services.invoice_service import create_direct_invoice


class LineItemInput(BaseModel):
    item_name: str
    quantity: float


class CreateInvoiceInput(BaseModel):
    customer_name: str = Field(..., description="Name of the customer")
    line_items: List[LineItemInput] = Field(..., description="Items to include in the invoice")


class CreateInvoiceTool(BaseTool):
    name = "create_invoice"
    description = "Create a direct tax invoice for a customer. Deducts stock automatically."
    input_schema = CreateInvoiceInput
    required_permissions = ["invoice:write"]
    risk_level = 1

    async def execute(
        self,
        input_data: CreateInvoiceInput,
        context: RequestContext,
        session: AsyncSession,
    ) -> ToolResult:
        
        # 1. Build task context
        customer, resolved_items = await context_builder.build_quotation_context(
            customer_name=input_data.customer_name,
            line_items=[i.model_dump() for i in input_data.line_items],
            business_id=context.business_id,
            session=session,
        )

        # 2. Execute deterministic business service
        data = await create_direct_invoice(
            session=session,
            tenant_id=context.business_id,
            customer=customer,
            items_with_qty=resolved_items,
        )

        return ToolResult(
            success=True,
            data=data,
        )
