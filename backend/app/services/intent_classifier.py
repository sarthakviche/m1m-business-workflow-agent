"""
M1M (Munim.ai) — Structured Intent Classifier
===============================================
Uses Gemini AI (gemini-3.6-flash) to extract structured business intents
and line-item entities from natural language messages.

Intents in scope for Sprint 1:
  - quotation
  - invoice
  - clarify
  - out_of_scope

Entities extracted:
  - customer_name
  - line_items: list of (item_name, quantity)
  - quotation_number (for quotation conversion)
  - is_quotation_conversion
  - confidence
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.gemini import DEFAULT_MODEL, get_gemini_client


class ExtractedLineItem(BaseModel):
    item_name: str = Field(description="Name or description of the product/item")
    quantity: float = Field(default=1.0, description="Quantity requested")


class IntentClassificationResult(BaseModel):
    intent: str = Field(
        description="One of: 'quotation', 'invoice', 'catalog_query', 'clarify', 'out_of_scope'"
    )
    confidence: float = Field(
        description="Classification confidence score between 0.0 and 1.0"
    )
    customer_name: Optional[str] = Field(
        default=None, description="Name of the customer or business mentioned"
    )
    line_items: List[ExtractedLineItem] = Field(
        default_factory=list, description="List of items and quantities"
    )
    quotation_number: Optional[str] = Field(
        default=None,
        description="Quotation number if converting a quote to an invoice (e.g. Q-202608-001)",
    )
    is_quotation_conversion: bool = Field(
        default=False,
        description="True if the user wants to convert an existing quotation to an invoice",
    )
    catalog_item_name: Optional[str] = Field(
        default=None,
        description="Name of item for price/stock/catalog queries",
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Clarifying question if information is missing or ambiguous",
    )


CLASSIFICATION_PROMPT = """You are the intent classification and entity extraction engine for M1M (Munim.ai), an AI business workflow agent for Indian SMEs.

Analyze the user's input message and conversation history, then return a JSON object strictly matching this JSON schema:
{
  "intent": "quotation" | "invoice" | "catalog_query" | "future_feature" | "off_topic" | "clarify" | "out_of_scope",
  "confidence": float (0.0 to 1.0),
  "customer_name": string | null,
  "line_items": [
    {"item_name": string, "quantity": float}
  ],
  "quotation_number": string | null,
  "is_quotation_conversion": boolean,
  "catalog_item_name": string | null,
  "clarification_question": string | null
}

CRITICAL CONTEXT & TYPO RULES:
- Correct common typos in user input (e.g., "craete" -> "create", "Steet" -> "Steel").
- If the user provides customer and items in a single message like "create a quotation for ramesh traders for TMT Steet rod 12mm 2 kg":
  - Extract customer_name: "ramesh traders"
  - Extract line_items: [{"item_name": "TMT Steel rod 12mm", "quantity": 2.0}]
- Quantities may appear before or after the item name (e.g., "2 kg TMT Steel rod" or "TMT Steel rod 12mm 2 kg").
- MULTI-TURN CONTEXT: If the assistant previously asked "Which items and quantities should be included for [Customer]?", and the user replies with item names (e.g., "TMT Steel rods"), retain intent="quotation" (or "invoice"), retain customer_name="[Customer]", and extract the line_items from the user's message.
- If the assistant previously asked "Which customer should this document be prepared for?", and the user replies with a name (e.g. "Ramesh Traders"), inherit the prior document intent and extract the customer_name.

RULES:
1. "quotation": User wants to prepare/create/send a quotation, estimate, or price quote for a customer.
   Example: "Create a quotation for Ramesh Traders for 5 TMT steel rods and 10 bolts"
2. "invoice": User wants to create/generate an invoice or convert a quotation into an invoice.
   Example: "Create an invoice for Ramesh Traders for 2 TMT steel rods"
   Example: "Convert quotation Q-202608-001 into an invoice"
3. "catalog_query": User asks about price, rate, stock level, or listing catalog items.
   Example: "What's the price of Steel Rod 12mm?"
   Example: "Do we have PVC pipe in stock?"
   Example: "Show me all items" / "list our catalog"
   Extract specific product name into catalog_item_name.
4. "future_feature": Request is a legitimate SME business feature not built yet in this sprint (e.g., payment/dues reminders, WhatsApp settings, accounting sync, dues follow-ups, salary slips).
   Example: "Remind my customers about dues"
5. "off_topic": Request is completely unrelated to business operations (e.g., writing python scripts/code, jokes, weather, general trivia, personal chat, recipes).
   Example: "Write me a python script to sort a list"
6. "clarify": The request is ambiguous, lacks critical information, or confidence is low (< 0.6).
7. Extract multiple line items if specified. If quantity is omitted, assume 1.0.
8. Return ONLY valid JSON. No surrounding markdown backticks or commentary.
"""


def _extract_via_regex(msg: str, conversation_context: str = "") -> IntentClassificationResult:
    """Helper fallback to extract entities via pattern matching."""
    lowered = msg.lower()

    # Off-topic check
    off_topic_kws = ("joke", "weather", "python", "code", "script", "poem", "story", "recipe", "game")
    if any(kw in lowered for kw in off_topic_kws):
        return IntentClassificationResult(intent="off_topic", confidence=0.9)

    # Future feature check
    future_kws = ("remind", "reminder", "due", "dues", "accounting", "salary", "whatsapp setting", "report")
    if any(kw in lowered for kw in future_kws) and not any(w in lowered for w in ("quote", "quotation", "invoice", "bill", "price", "stock")):
        return IntentClassificationResult(intent="future_feature", confidence=0.9)

    quote_match = re.search(r"Q-\d{6}-\d+", msg, re.IGNORECASE)

    # Conversion
    if "convert" in lowered and ("quot" in lowered or quote_match):
        q_num = quote_match.group(0).upper() if quote_match else None
        return IntentClassificationResult(
            intent="invoice",
            confidence=0.95,
            is_quotation_conversion=True,
            quotation_number=q_num,
        )

    # Detect quotation vs invoice vs catalog (with typo tolerance)
    is_quote = any(w in lowered for w in ("quote", "quotation", "estimate", "craete a quote", "craete a quotation"))
    is_inv = any(w in lowered for w in ("invoice", "bill", "tax invoice"))
    catalog_kws = ("price", "rate", "cost", "stock", "catalog", "items", "how much is", "what is the price", "do we have")
    is_catalog = any(kw in lowered for kw in catalog_kws) and not is_quote and not is_inv

    if is_catalog:
        item_match = re.search(r"(?:of|for|is|have)\s+([A-Za-z0-9\s]+?)(?:\s+in\s+stock|\?|$)", msg, re.IGNORECASE)
        item_name = item_match.group(1).strip() if item_match else None
        return IntentClassificationResult(
            intent="catalog_query",
            confidence=0.85,
            catalog_item_name=item_name,
        )

    # Multi-turn context check for fallback
    if not is_quote and not is_inv and conversation_context:
        # Check if assistant asked for items for a specific customer
        item_ask_match = re.search(r"items and quantities should be included for \*\*([^*]+)\*\*", conversation_context, re.IGNORECASE)
        if item_ask_match:
            cust_name = item_ask_match.group(1).strip()
            # Treat raw message as line item
            qty_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|pcs|mtr|box|l|ton|mm)?", msg, re.IGNORECASE)
            qty = float(qty_m.group(1)) if qty_m else 1.0
            return IntentClassificationResult(
                intent="quotation",
                confidence=0.8,
                customer_name=cust_name,
                line_items=[ExtractedLineItem(item_name=msg.strip(), quantity=qty)],
            )

    if not is_quote and not is_inv:
        return IntentClassificationResult(
            intent="clarify",
            confidence=0.5,
            clarification_question="Could you please specify whether you would like to create a quotation, invoice, or check item prices/stock?",
        )

    intent_type = "quotation" if is_quote else "invoice"

    # Split by " for " or " to " to isolate customer vs items
    # e.g. "create a quotation for ramesh traders for TMT Steet rod 12mm 2 kg"
    for_parts = re.split(r"\s+for\s+", msg, flags=re.IGNORECASE)
    if len(for_parts) >= 3:
        c_name = for_parts[1].strip()
        item_raw = for_parts[2].strip()

        qty_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|pcs|mtr|box|ltr|ton|bags|pieces|units)\b", item_raw, re.IGNORECASE)
        if not qty_match:
            qty_match = re.search(r"^\s*(\d+(?:\.\d+)?)\b|\b(\d+(?:\.\d+)?)\s*$", item_raw, re.IGNORECASE)

        qty = 1.0
        i_name = item_raw
        if qty_match:
            qty_str = qty_match.group(1) or (qty_match.group(2) if len(qty_match.groups()) > 1 else None)
            if qty_str:
                qty = float(qty_str)
            cleaned = re.sub(r"\b" + re.escape(qty_match.group(0).strip()) + r"\b", "", item_raw, flags=re.IGNORECASE).strip()
            if cleaned:
                i_name = cleaned

        return IntentClassificationResult(
            intent=intent_type,
            confidence=0.9,
            customer_name=c_name,
            line_items=[ExtractedLineItem(item_name=i_name, quantity=qty)],
        )

    # Pattern: "... for <customer> for <qty> <item>"
    pat = re.search(r"(?:for|to)\s+([A-Za-z0-9\s]+?)\s+(?:for|with)\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9\s]+)", msg, re.IGNORECASE)
    if pat:
        c_name = pat.group(1).strip()
        qty = float(pat.group(2))
        i_name = pat.group(3).strip()
        return IntentClassificationResult(
            intent=intent_type,
            confidence=0.9,
            customer_name=c_name,
            line_items=[ExtractedLineItem(item_name=i_name, quantity=qty)],
        )

    # Pattern: "... for <customer>"
    pat_cust = re.search(r"(?:for|to)\s+([A-Za-z0-9\s]+)", msg, re.IGNORECASE)
    c_name = pat_cust.group(1).strip() if pat_cust else None
    if c_name and re.match(r"^\d", c_name):
        c_name = None

    return IntentClassificationResult(
        intent=intent_type,
        confidence=0.75,
        customer_name=c_name,
        line_items=[],
    )


def classify_intent_sync(raw_message: str, conversation_context: str = "") -> IntentClassificationResult:
    """
    Synchronously classify raw user message using Gemini with regex fallback.
    
    Parameters
    ----------
    raw_message : str
        The current user message
    conversation_context : str
        Full conversation history for context awareness
    """
    msg = (raw_message or "").strip()
    if not msg:
        return IntentClassificationResult(
            intent="clarify",
            confidence=1.0,
            clarification_question="Please provide details for the quotation or invoice you would like to create.",
        )

    try:
        client = get_gemini_client()
        
        # Build prompt with conversation context
        context_section = ""
        if conversation_context.strip():
            context_section = f"\n\nConversation history:\n{conversation_context}\n"
        
        prompt = f"{CLASSIFICATION_PROMPT}{context_section}\n\nUser message: \"{msg}\""

        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
        )
        resp_text = (response.text or "").strip()

        # Extract JSON object from response
        json_match = re.search(r"\{.*\}", resp_text, re.DOTALL)
        if not json_match:
            return _extract_via_regex(msg, conversation_context)

        data = json.loads(json_match.group(0))
        result = IntentClassificationResult(**data)

        # Sanitize customer_name: if it starts with digits, it's item quantity not a customer name
        if result.customer_name and re.match(r"^\d", result.customer_name.strip()):
            result.customer_name = None

        # Apply confidence and missing field routing rules
        if result.confidence < 0.6:
            result.intent = "clarify"
            if not result.clarification_question:
                result.clarification_question = (
                    "Could you please clarify your request? Are you looking to create a quotation or an invoice?"
                )

        return result

    except Exception:
        res = _extract_via_regex(msg, conversation_context)
        if res.customer_name and re.match(r"^\d", res.customer_name.strip()):
            res.customer_name = None
        return res
