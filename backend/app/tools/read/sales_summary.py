"""Read-only chat tool for deterministic sales totals."""

from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.context import RequestContext
from app.services.business_insights import period_label, sales_summary
from app.services.number_format import format_inr
from app.tools.base import BaseTool
from app.tools.schemas import ToolResult


class SalesSummaryInput(BaseModel):
    period: Literal["today", "this_week", "this_month", "last_month"] = "this_week"


class SalesSummaryTool(BaseTool):
    name = "sales_summary"
    description = "Read invoice sales for today, this week, this month, or last month."
    input_schema = SalesSummaryInput
    required_permissions = ["invoice:read"]
    risk_level = 0

    async def execute(self, input_data: SalesSummaryInput, context: RequestContext, session: AsyncSession) -> ToolResult:
        summary = await sales_summary(session, context.business_id, input_data.period)
        label = period_label(input_data.period)
        invoice_word = "invoice" if summary.invoice_count == 1 else "invoices"
        return ToolResult(
            success=True,
            data={"response_text": f"**Sales {label}:** ₹{format_inr(summary.total)} from {summary.invoice_count} {invoice_word}."},
        )
