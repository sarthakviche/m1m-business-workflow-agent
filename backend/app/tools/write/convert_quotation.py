"""
Munim.ai — Convert Quotation Tool
"""

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.tools.schemas import ToolResult
from app.orchestrator.context import RequestContext
from app.services.invoice_service import convert_quotation_to_invoice


class ConvertQuotationInput(BaseModel):
    quotation_number: str = Field(..., description="Quotation number to convert (e.g. Q-202610-001)")


class ConvertQuotationTool(BaseTool):
    name = "convert_quotation"
    description = "Convert an existing quotation into a tax invoice."
    input_schema = ConvertQuotationInput
    required_permissions = ["invoice:write"]
    risk_level = 1

    async def execute(
        self,
        input_data: ConvertQuotationInput,
        context: RequestContext,
        session: AsyncSession,
    ) -> ToolResult:
        
        # Execute deterministic business service
        data = await convert_quotation_to_invoice(
            session=session,
            tenant_id=context.business_id,
            quotation_identifier=input_data.quotation_number,
        )

        return ToolResult(
            success=True,
            data=data,
        )
