"""Read-only chat tool for deterministic low-stock items."""

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestrator.context import RequestContext
from app.services.business_insights import LOW_STOCK_THRESHOLD, low_stock_items
from app.services.number_format import format_quantity
from app.tools.base import BaseTool
from app.tools.schemas import ToolResult


class LowStockInput(BaseModel):
    pass


class LowStockTool(BaseTool):
    name = "low_stock"
    description = "Read catalog items at or below the low-stock threshold."
    input_schema = LowStockInput
    required_permissions = ["catalog:read"]
    risk_level = 0

    async def execute(self, input_data: LowStockInput, context: RequestContext, session: AsyncSession) -> ToolResult:
        items = await low_stock_items(session, context.business_id)
        if not items:
            text = f"No items are at or below {format_quantity(LOW_STOCK_THRESHOLD)} units in stock."
        else:
            lines = [f"**Low stock (at or below {format_quantity(LOW_STOCK_THRESHOLD)}):**"]
            lines.extend(f"• **{item.name}** — {format_quantity(item.quantity)} {item.unit}" for item in items)
            text = "\n".join(lines)
        return ToolResult(success=True, data={"response_text": text})
