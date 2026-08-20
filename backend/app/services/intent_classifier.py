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
        description="One of: 'quotation', 'invoice', 'clarify', 'out_of_scope'"
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
    clarification_question: Optional[str] = Field(
        default=None,
        description="Clarifying question if information is missing or ambiguous",
    )


CLASSIFICATION_PROMPT = """You are the intent classification and entity extraction engine for M1M (Munim.ai), an AI business workflow agent for Indian SMEs.

Analyze the user's input message and conversation history, then return a JSON object strictly matching this JSON schema:
{
  "intent": "quotation" | "invoice" | "clarify" | "out_of_scope",
  "confidence": float (0.0 to 1.0),
  "customer_name": string | null,
  "line_items": [
    {"item_name": string, "quantity": float}
  ],
  "quotation_number": string | null,
  "is_quotation_conversion": boolean,
  "clarification_question": string | null
}

CRITICAL CONTEXT RULES:
- If the user says only "Quotation" or "Invoice", remember the previous context to understand they are answering which document type they want.
- If the user says only "Quotation" and prior context shows bot asked "Would you like quotation or invoice?", interpret this as intent="quotation".
- If the user provides customer name and items in the current message (e.g., "Ramesh Enterprises 5 bags Rockwool"), extract both.
- Look back at conversation history to fill in missing information that was mentioned earlier.

RULES:
1. "quotation": User wants to prepare/create/send a quotation, estimate, or price quote for a customer.
   Example: "Create a quotation for Ramesh Traders for 5 TMT steel rods and 10 bolts"
2. "invoice": User wants to create/generate an invoice or convert a quotation into an invoice.
   Example: "Create an invoice for Ramesh Traders for 2 TMT steel rods"
   Example: "Convert quotation Q-202608-001 into an invoice"
3. "clarify": The request is ambiguous, lacks critical information, or confidence is low (< 0.6).
4. "out_of_scope": The request is about stock queries, payment dues reminders, WhatsApp settings, accounting reports, or unrelated chit-chat (not quote/invoice creation).
5. Extract multiple line items if specified. If quantity is omitted, assume 1.0.
6. For quotation conversions, extract the quotation number (e.g. Q-202608-001) and set is_quotation_conversion to true.
7. Return ONLY valid JSON. No surrounding markdown backticks or commentary.
"""


def _extract_via_regex(msg: str) -> IntentClassificationResult:
    """Helper fallback to extract entities via pattern matching."""
    lowered = msg.lower()
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

    # Detect quotation vs invoice
    is_quote = any(w in lowered for w in ("quote", "quotation", "estimate"))
    is_inv = any(w in lowered for w in ("invoice", "bill", "tax invoice"))

    if not is_quote and not is_inv:
        return IntentClassificationResult(
            intent="clarify",
            confidence=0.5,
            clarification_question="Could you please specify whether you would like to create a quotation or an invoice?",
        )

    intent_type = "quotation" if is_quote else "invoice"

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
            return _extract_via_regex(msg)

        data = json.loads(json_match.group(0))
        result = IntentClassificationResult(**data)

        # Apply confidence and missing field routing rules
        if result.confidence < 0.6:
            result.intent = "clarify"
            if not result.clarification_question:
                result.clarification_question = (
                    "Could you please clarify your request? Are you looking to create a quotation or an invoice?"
                )

        return result

    except Exception:
        return _extract_via_regex(msg)
