"""
Munim.ai — Search Products Tool
"""

from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.tools.schemas import ToolResult
from app.orchestrator.context import RequestContext
from app.services.catalog_service import list_catalog_summary, lookup_catalog_item_details


class SearchProductsInput(BaseModel):
    item_name: Optional[str] = Field(None, description="Specific item to look up. Leave empty to list all products.")


class SearchProductsTool(BaseTool):
    name = "search_products"
    description = "Lookup prices, GST rates, and available stock for a specific item, or list the entire catalog."
    input_schema = SearchProductsInput
    required_permissions = ["catalog:read"]
    risk_level = 0

    async def execute(
        self,
        input_data: SearchProductsInput,
        context: RequestContext,
        session: AsyncSession,
    ) -> ToolResult:
        
        if input_data.item_name:
            details = await lookup_catalog_item_details(
                session=session,
                tenant_id=context.business_id,
                item_name=input_data.item_name,
            )
            if details["found"]:
                hsn_str = f" (HSN: {details['hsn_code']})" if details.get("hsn_code") else ""
                response_text = (
                    f"**{details['name']}**{hsn_str}:\n"
                    f"• Unit Price: ₹{details['unit_price']:.2f} per {details['unit']}\n"
                    f"• GST Rate: {details['gst_rate_percent']:.0f}%\n"
                    f"• Stock Available: {details['stock_available']:.2f} {details['unit']}"
                )
            else:
                response_text = f"Item **'{input_data.item_name}'** was not found in your catalog. Please check the item name."
            data = details
        else:
            summary = await list_catalog_summary(
                session=session,
                tenant_id=context.business_id,
                limit=6
            )
            lines = [f"Here are items from your catalog ({summary['total_count']} total):"]
            for item in summary["displayed_items"]:
                lines.append(f"• **{item['name']}** — ₹{item['unit_price']:.2f}/{item['unit']} ({item['gst_rate_percent']:.0f}% GST) | Stock: {item['stock_available']} {item['unit']}")
            if summary["has_more"]:
                lines.append(f"\n_Showing first 6 of {summary['total_count']} items._")
            response_text = "\n".join(lines)
            data = summary

        return ToolResult(
            success=True,
            data={"response_text": response_text, **data},
        )
