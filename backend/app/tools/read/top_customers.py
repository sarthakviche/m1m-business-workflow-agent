"""Read-only chat tool for deterministic top-customer totals."""

from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.context import RequestContext
from app.services.business_insights import period_label, top_customers
from app.services.number_format import format_inr
from app.tools.base import BaseTool
from app.tools.schemas import ToolResult


class TopCustomersInput(BaseModel):
    period: Literal["today", "this_week", "this_month", "last_month"] = "this_month"


class TopCustomersTool(BaseTool):
    name = "top_customers"
    description = "Read the top three customers by issued invoice sales for a period."
    input_schema = TopCustomersInput
    required_permissions = ["invoice:read", "customer:read"]
    risk_level = 0

    async def execute(self, input_data: TopCustomersInput, context: RequestContext, session: AsyncSession) -> ToolResult:
        customers = await top_customers(session, context.business_id, input_data.period)
        label = period_label(input_data.period)
        if not customers:
            text = f"No invoice sales were recorded {label}."
        else:
            lines = [f"**Top customers {label}:**"]
            lines.extend(f"{index}. **{customer.name}** — ₹{format_inr(customer.total)}" for index, customer in enumerate(customers, start=1))
            text = "\n".join(lines)
        return ToolResult(success=True, data={"response_text": text})
