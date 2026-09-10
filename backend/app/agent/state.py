"""
M1M (Munim.ai) — LangGraph AgentState Definition
==================================================
Typed state dictionary per TRD Section 5.1 for LangGraph workflow execution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


class ConversationMessage(TypedDict, total=False):
    """Single message in conversation history."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[str]


class AgentState(TypedDict, total=False):
    """
    Workflow state passed through LangGraph nodes.
    """
    # Multi-tenant and session routing context
    tenant_id: str
    user_id: Optional[str]
    channel: Literal["whatsapp", "web"]
    raw_message: str
    
    # Conversation history for context awareness
    conversation_history: List[ConversationMessage]
    full_conversation_text: str  # Full conversation for context in intent classifier

    # Intent and entity classification
    detected_intent: Optional[Literal["quotation", "invoice", "catalog_query", "future_feature", "off_topic", "clarify", "out_of_scope"]]
    extracted_entities: Dict[str, Any]
    missing_fields: List[str]
    confidence: float

    # Output and response
    draft_document_id: Optional[str]
    response_text: str
    response_attachments: Optional[List[Dict[str, Any]]]
    requires_confirmation: bool

    # Customer matching confirmation state
    customer_match_pending: bool
    customer_match_candidate_name: Optional[str]
    customer_match_candidate_id: Optional[str]
    customer_match_input_name: Optional[str]
    customer_was_auto_created: bool

    # Document details for API responses
    document_type: Optional[Literal["quotation", "invoice"]]
    document_id: Optional[str]
    document_number: Optional[str]
    data: Optional[Dict[str, Any]]

