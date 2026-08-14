"""
agents/state.py — AgentState TypedDict (TRD Section 5.1).
Implemented literally as specified.
"""
from typing import TypedDict, Optional, Literal


class AgentState(TypedDict):
    tenant_id: str
    user_id: str
    channel: Literal["whatsapp", "web"]
    raw_message: str
    detected_intent: Optional[Literal["quotation", "invoice", "dues", "stock", "summary", "clarify", "out_of_scope"]]
    extracted_entities: Optional[dict]      # customer_name, item_name, quantity, etc.
    missing_fields: Optional[list[str]]
    draft_document_id: Optional[str]
    response_text: Optional[str]
    response_attachments: Optional[list[dict]]  # [{"type": "pdf", "url": "..."}]
    requires_confirmation: bool
