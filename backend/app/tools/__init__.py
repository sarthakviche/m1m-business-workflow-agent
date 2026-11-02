"""
Munim.ai — Tools Package
"""

from app.tools.registry import registry
from app.tools.write.create_quotation import CreateQuotationTool
from app.tools.write.create_invoice import CreateInvoiceTool
from app.tools.write.convert_quotation import ConvertQuotationTool
from app.tools.read.search_products import SearchProductsTool


def register_all_tools() -> None:
    """Registers all available tools in the central registry."""
    # Only register if not already registered (avoids issues in test reloads)
    if "create_quotation" not in registry._tools:
        registry.register(CreateQuotationTool())
    if "create_invoice" not in registry._tools:
        registry.register(CreateInvoiceTool())
    if "convert_quotation" not in registry._tools:
        registry.register(ConvertQuotationTool())
    if "search_products" not in registry._tools:
        registry.register(SearchProductsTool())


# Auto-register on import
register_all_tools()

__all__ = ["registry", "register_all_tools"]
