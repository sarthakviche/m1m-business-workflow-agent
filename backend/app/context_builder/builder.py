"""
Munim.ai — Context Builder
============================
Fetches task-specific data needed by the tools.
Ensures we don't dump the whole DB into the model context.
All lookups strictly enforce business_id isolation.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.item import Item
from app.services.customer_lookup import lookup_customer_scored, create_customer_if_missing
from app.services.item_lookup import lookup_item
from app.errors.categories import InsufficientInformationError, NotFoundError


class ContextBuilder:
    """
    Builds context objects for tools by securely querying the database.
    """

    async def build_quotation_context(
        self,
        customer_name: str,
        line_items: list[dict],
        business_id: uuid.UUID,
        session: AsyncSession,
    ) -> Tuple[Customer, List[Tuple[Item, Decimal]]]:
        """
        Loads the customer and items required for a quotation or invoice.
        Creates customer if missing.
        Raises InsufficientInformationError if any item is not found.

        Items are resolved before the customer so a request that fails on an
        unknown item never leaves a newly created customer behind.
        """
        resolved_items = await self._resolve_items(line_items, business_id, session)

        # 1. Resolve customer
        match_result = await lookup_customer_scored(session, business_id, customer_name)
        if match_result.match_type in ("exact", "fuzzy_high"):
            customer = match_result.customer
        elif match_result.match_type == "fuzzy_medium":
            raise InsufficientInformationError(
                detail=f"Fuzzy match pending for {customer_name}",
                user_message=f"Did you mean **{match_result.customer.name}**? Or is this a new customer?"
            )
        else:
            customer = await create_customer_if_missing(session, business_id, customer_name)

        return customer, resolved_items

    async def _resolve_items(
        self,
        line_items: list[dict],
        business_id: uuid.UUID,
        session: AsyncSession,
    ) -> List[Tuple[Item, Decimal]]:
        """Match each requested line to a catalog item; never invent items or quantities."""
        resolved_items: List[Tuple[Item, Decimal]] = []
        missing_items = []

        for li in line_items:
            item_name = li.get("item_name", li.get("name"))
            qty_val = li.get("quantity", li.get("qty"))

            # Never guess a quantity: an unreadable or non-positive value goes
            # back to the user instead of silently becoming 1.
            try:
                qty = Decimal(str(qty_val))
            except Exception:
                qty = None
            if qty is None or not qty.is_finite() or qty <= 0:
                raise InsufficientInformationError(
                    detail=f"Invalid quantity {qty_val!r} for {item_name!r}",
                    user_message=f"What quantity of **{item_name}** should I include?",
                )

            item = await lookup_item(session, business_id, item_name)
            if item:
                resolved_items.append((item, qty))
            else:
                missing_items.append(item_name)

        if missing_items:
            # If items are missing, we raise this to trigger the fallback catalog display
            from app.services.catalog_service import list_catalog_summary
            catalog_text = await list_catalog_summary(session, business_id)
            
            names = ", ".join(f"'{m}'" for m in missing_items)
            msg = f"Item(s) {names} wasn't found in your catalog.\n\nHere is what is available:\n{catalog_text}\n\nPlease reply with the item name and quantity from the list."
            raise InsufficientInformationError(
                detail=f"Missing items: {missing_items}",
                user_message=msg,
            )

        return resolved_items


# Global singleton
context_builder = ContextBuilder()
