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
    # None means the user did not state a quantity. It is never guessed: the
    # agent asks for it instead (see app.agent.graph).
    quantity: Optional[float] = Field(default=None, description="Quantity requested; null if not stated")


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


CLASSIFICATION_PROMPT = """You are the intent classification and entity extraction engine for Munim (M1M), a business workflow AI for Indian SMEs.

The business is an industrial supplier. Its catalog contains items like steel rods, steel plates, bolts, nuts, washers, and other industrial hardware.

Analyze the CURRENT user message together with the conversation history, then return ONLY a valid JSON object matching this schema — no markdown, no explanation:
{
  "intent": "quotation" | "invoice" | "catalog_query" | "future_feature" | "off_topic" | "clarify" | "out_of_scope",
  "confidence": float (0.0 to 1.0),
  "customer_name": string | null,
  "line_items": [{"item_name": string, "quantity": float}],
  "quotation_number": string | null,
  "is_quotation_conversion": boolean,
  "catalog_item_name": string | null,
  "clarification_question": string | null
}

=== INTENT RULES ===

1. "quotation": User wants to create a quotation/estimate/price quote for a customer.
2. "invoice": User wants to create a GST invoice, OR convert a quotation to an invoice.
3. "catalog_query": User asks about item prices, rates, stock levels, or wants to see the catalog.
4. "future_feature": Legitimate SME feature not yet built (dues reminders, accounting sync, salary slips, reports).
5. "off_topic": Completely unrelated to business (jokes, code, weather, recipes, general chat).
6. "clarify": Ambiguous request, or missing BOTH customer AND items with no prior context to resolve them.

=== ENTITY EXTRACTION RULES ===

CUSTOMER NAME:
- Extract business/person name from phrases like "for X", "to X", "of X".
- Do NOT confuse a quantity or number as a customer name.
- If customer name starts with a digit, set customer_name = null.

LINE ITEMS:
- Extract ALL items and quantities mentioned in the message.
- Quantities may appear before or after the item name: "10 kg TMT Steel Rod" or "TMT Steel Rod 10 kg".
- Multiple items separated by "and", commas, or newlines should ALL be extracted.
- IMPORTANT: Extract item names exactly as mentioned — do NOT check if they exist in the catalog here.
- If no quantity is mentioned for an item, set quantity to null. NEVER assume 1 or any other number.
- Numbers that are part of an item's specification (12mm, M12, 6205, 2.5sqmm, 1 Ton, 5kg Box) are NOT quantities.
- If the user mentions items without specifying a document type (quotation/invoice), still extract them.

MULTI-TURN CONTEXT — CRITICAL RULES:
- If conversation history shows the assistant asked "Which items and quantities should be included for **X**?" — and the current message contains item names/quantities — set intent = (same as prior turn: quotation or invoice), customer_name = X, and extract line_items from the current message.
- If conversation history shows the assistant asked "Which customer should this document be prepared for?" — and the current message is a customer name — set intent = (prior intent), customer_name = current message.
- If conversation history shows a quotation or invoice was being created for customer X with items Y — and the user says "actually make it an invoice" or "change to quotation" — set intent accordingly, re-use customer_name = X and line_items = Y from history.
- NEVER lose context from prior turns when the user is answering a clarification question.

QUOTATION CONVERSION:
- Set is_quotation_conversion = true and extract quotation_number when user says "convert Q-XXXXXX-XXX to invoice" or "make Q-XXXXXX-XXX an invoice".

=== CONFIDENCE ===
- Set confidence >= 0.85 when intent is clear and at least customer_name OR line_items are present.
- Set confidence = 0.5 and intent = "clarify" ONLY when the message is truly ambiguous with no context.

=== EXAMPLES ===

User: "Create a quotation for Ramesh Traders, 10 kg TMT Steel Rod 12mm and 50 pcs MS Hex Bolt"
-> intent=quotation, customer_name="Ramesh Traders", line_items=[{item_name:"TMT Steel Rod 12mm", quantity:10}, {item_name:"MS Hex Bolt", quantity:50}]

User: "Make an invoice for Patel Constructions for 5 kg steel plate and 20 bolts"
-> intent=invoice, customer_name="Patel Constructions", line_items=[{item_name:"steel plate", quantity:5}, {item_name:"bolts", quantity:20}]

History: assistant said "Which items and quantities for **Ganesh Engineering Works**?"
User: "20 kg TMT Steel Rod 12mm"
-> intent=quotation, customer_name="Ganesh Engineering Works", line_items=[{item_name:"TMT Steel Rod 12mm", quantity:20}]

History: user was creating a quotation for Ramesh Traders with TMT Steel Rod 10 kg
User: "Actually make it an invoice"
-> intent=invoice, customer_name="Ramesh Traders", line_items=[{item_name:"TMT Steel Rod 12mm", quantity:10}]

User: "What is the price of TMT Steel Rod?"
-> intent=catalog_query, catalog_item_name="TMT Steel Rod"

User: "Show all items" / "What do we have in stock?"
-> intent=catalog_query, catalog_item_name=null

User: "Tell me a joke"
-> intent=off_topic

User: "Remind my customer about dues"
-> intent=future_feature
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
            # Treat the message as the item list. A bare item name keeps
            # quantity=None so the agent asks for it; numbers inside a spec
            # ("12mm") are not read as quantities.
            items = _rescue_line_items(msg) or [ExtractedLineItem(item_name=msg.strip(), quantity=None)]
            return IntentClassificationResult(
                intent="quotation",
                confidence=0.8,
                customer_name=cust_name,
                line_items=items,
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

        qty = None
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


def _rescue_line_items(msg: str) -> List[ExtractedLineItem]:
    """
    Best-effort regex extraction of item lines from a message.
    Handles patterns like:
      - "10 kg TMT Steel Rod 12mm and 50 pcs MS Hex Bolt"
      - "TMT Steel Rod 12mm 10 kg, MS Nut 50 pcs"
    """
    # Split on " and ", commas between items
    candidates = re.split(r'\s+and\s+|,\s*(?=\d|\w)', msg, flags=re.IGNORECASE)
    items = []
    for seg in candidates:
        seg = seg.strip()
        if not seg:
            continue
        # Pattern: qty [unit] item_name OR item_name qty [unit]
        m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:kg|pcs|mtr|box|ltr|ton|bags|pieces|units|nos)?\s+(.+)$', seg, re.IGNORECASE)
        if m:
            qty = float(m.group(1))
            name = m.group(2).strip()
            items.append(ExtractedLineItem(item_name=name, quantity=qty))
            continue
        m2 = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?)\s*(?:kg|pcs|mtr|box|ltr|ton|bags|pieces|units|nos)?$', seg, re.IGNORECASE)
        if m2:
            name = m2.group(1).strip()
            qty = float(m2.group(2))
            # Only use if name looks like an item (not a pure number or customer word)
            if not re.match(r'^\d', name) and len(name) > 3:
                items.append(ExtractedLineItem(item_name=name, quantity=qty))
    return items


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

        from google import genai
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IntentClassificationResult,
                temperature=0.1
            ),
        )
        resp_text = (response.text or "").strip()

        data = json.loads(resp_text)
        result = IntentClassificationResult(**data)

        # Sanitize customer_name: if it starts with digits, it's item quantity not a customer name
        if result.customer_name and re.match(r"^\d", result.customer_name.strip()):
            result.customer_name = None

        # ── Post-LLM rescue: if LLM returned no line_items but msg has quantities, extract them ──
        if not result.line_items and result.intent in ("quotation", "invoice", "clarify"):
            rescued = _rescue_line_items(msg)
            if rescued:
                result.line_items = rescued
                # If we now have both customer + items and were clarify, promote intent
                if result.intent == "clarify" and result.customer_name and result.line_items:
                    # Check if message had quotation/invoice keywords
                    lowered = msg.lower()
                    if any(w in lowered for w in ("quote", "quotation", "estimate")):
                        result.intent = "quotation"
                        result.confidence = 0.85
                    elif any(w in lowered for w in ("invoice", "bill", "tax")):
                        result.intent = "invoice"
                        result.confidence = 0.85

        # ── Promote clarify→quotation/invoice when context has prior intent established ──
        if result.intent == "clarify" and conversation_context:
            # Check if assistant previously asked for items for a known customer
            m = re.search(
                r"items and quantities.*?for \*\*([^*]+)\*\*",
                conversation_context, re.IGNORECASE
            )
            if m and result.line_items:
                # Prior intent detection from context
                ctx_lower = conversation_context.lower()
                prior_intent = "quotation"
                if "invoice" in ctx_lower and "quotation" not in ctx_lower[:ctx_lower.find("invoice")]:
                    prior_intent = "invoice"
                result.intent = prior_intent
                result.customer_name = result.customer_name or m.group(1).strip()
                result.confidence = 0.88

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
