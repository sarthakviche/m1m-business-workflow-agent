"""Read-only chat tool for customer outstanding balances."""

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.context import RequestContext
from app.services.business_insights import outstanding_dues
from app.services.number_format import format_inr
from app.tools.base import BaseTool
from app.tools.schemas import ToolResult


class OutstandingDuesInput(BaseModel):
    pass


class OutstandingDuesTool(BaseTool):
    name = "outstanding_dues"
    description = "Read which customers currently have the largest unpaid invoice balances."
    input_schema = OutstandingDuesInput
    required_permissions = ["invoice:read", "customer:read"]
    risk_level = 0

    async def execute(self, input_data: OutstandingDuesInput, context: RequestContext, session: AsyncSession) -> ToolResult:
        dues = await outstanding_dues(session, context.business_id)
        if not dues:
            text = "You have no outstanding invoice dues."
        else:
            lines = ["**Customers with the highest dues:**"]
            lines.extend(f"• **{due.customer_name}** — ₹{format_inr(due.amount)}" for due in dues)
            text = "\n".join(lines)
        return ToolResult(success=True, data={"response_text": text})
