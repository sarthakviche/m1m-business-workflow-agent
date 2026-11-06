"""
M1M (Munim.ai) — LangGraph Workflow Definition
================================================
Orchestrates intent classification, quotation agent, invoice agent,
and conversation logging.

Flow:
  START → classify_intent → [quotation_agent | invoice_agent | clarify_agent | out_of_scope_agent] → log_conversation → END
"""

from __future__ import annotations

import asyncio
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Tuple

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.db.session import AsyncSessionLocal
from app.models.conversation_log import ConversationLog
from app.models.customer import Customer
from app.models.item import Item
from app.services.catalog_service import lookup_catalog_item_details, list_catalog_summary
from app.services.customer_lookup import lookup_customer_scored, create_customer_if_missing
from app.services.ai_quota import reserve_ai_call
from app.services.intent_classifier import classify_intent_sync, classify_with_rules
from app.services.invoice_service import (
    InsufficientStockError,
    QuotationNotFoundError,
    convert_quotation_to_invoice,
    create_direct_invoice,
)
from app.services.item_lookup import lookup_item
from app.services.quotation_service import create_quotation


_AI_LIMIT_NOTE = (
    "\n\n_I've reached today's limit for understanding free-form requests, so please be specific for now. "
    "For example: Create quotation for Ramesh Traders for 10 Steel Rod 12mm._"
)


@asynccontextmanager
async def _get_session(config: RunnableConfig) -> AsyncIterator[AsyncSession]:
    """Helper to obtain AsyncSession from RunnableConfig or fallback to AsyncSessionLocal."""
    conf = config or {}
    configurable = conf.get("configurable") or {}
    session = configurable.get("session")
    if session is not None:
        yield session
    else:
        async with AsyncSessionLocal() as sess:
            yield sess
            await sess.commit()


async def classify_intent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Classifies user message intent and extracts structured entities with conversation context."""
    from app.conversation.store import conversation_store
    from app.conversation.state import ConversationState

    context = config["configurable"]["request_context"]
    raw_message = state.get("raw_message", "")
    conversation_context = state.get("full_conversation_text", "")
    
    async with _get_session(config) as session:
        # 1. Load existing state
        conv_state = await conversation_store.get(context.conversation_id, context.business_id, session)
        if not conv_state:
            conv_state = ConversationState(
                conversation_id=context.conversation_id,
                business_id=context.business_id
            )

        # 2. Extract new entities. The Gemini SDK call is blocking, so run it off
        # the event loop to keep other chats responsive. Over the daily AI limit,
        # the rule-based parser takes over.
        ai_allowed = await reserve_ai_call(session, context.business_id)
        if ai_allowed:
            res = await asyncio.to_thread(classify_intent_sync, raw_message, conversation_context)
        else:
            res = classify_with_rules(raw_message, conversation_context)
        resolved = await _resolve_intent(conv_state, res, raw_message, session)
        if not ai_allowed and resolved["detected_intent"] == "clarify":
            resolved["response_text"] += _AI_LIMIT_NOTE
        return resolved


# A reply that is only a quantity, e.g. "50", "50 pcs", "12.5 kg".
_BARE_QUANTITY = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(?:kg|kgs|pcs|pc|nos|units?|pieces?|mtr|m|box|boxes|ltr|l|ton|tons|bags?)?\s*\.?\s*$",
    re.IGNORECASE,
)


def _items_missing_quantity(entities: Dict[str, Any]) -> List[str]:
    return [li.get("item_name") or "item" for li in entities.get("line_items") or [] if li.get("quantity") is None]


def _fill_missing_quantity(conv_state, raw_message: str) -> bool:
    """Answer to "How many X?": put a bare quantity on the first line still missing one."""
    match = _BARE_QUANTITY.match(raw_message or "")
    if not match:
        return False
    for li in conv_state.extracted_entities.get("line_items") or []:
        if li.get("quantity") is None:
            li["quantity"] = float(match.group(1))
            return True
    return False


async def _resolve_intent(conv_state, res, raw_message: str, session: AsyncSession) -> Dict[str, Any]:
    """Merge a classification into the conversation state and decide what is still missing."""
    from app.conversation.store import conversation_store

    # 3. Handle intent continuation
    detected_intent = res.intent
    if detected_intent in ("unknown", "clarify") and conv_state.pending_intent:
        detected_intent = conv_state.pending_intent

    # 4. Merge entities. A bare quantity answering "How many X?" is applied
    # directly. Otherwise, a message naming both a customer and items is a
    # complete request on its own: start fresh so leftovers from an earlier,
    # unfinished request can never leak into this document.
    if conv_state.pending_intent and _fill_missing_quantity(conv_state, raw_message):
        detected_intent = conv_state.pending_intent
        res = res.model_copy(update={"customer_name": None, "line_items": [], "catalog_item_name": None})
    elif res.customer_name and res.line_items:
        conv_state.extracted_entities = {}
    conv_state.update_entities({
        "customer_name": res.customer_name,
        "line_items": [i.model_dump() for i in res.line_items] if res.line_items else None,
        "quotation_number": res.quotation_number,
        "is_quotation_conversion": res.is_quotation_conversion,
        "catalog_item_name": res.catalog_item_name,
    })

    extracted = conv_state.extracted_entities
    missing_fields: List[str] = []

    # 5. Determine missing fields based on MERGED state
    if detected_intent == "quotation":
        if not extracted.get("customer_name"):
            missing_fields.append("customer_name")
        if not extracted.get("line_items"):
            missing_fields.append("line_items")
        elif _items_missing_quantity(extracted):
            missing_fields.append("quantity")
        if missing_fields:
            detected_intent = "clarify"
            conv_state.pending_intent = "quotation"
        else:
            conv_state.pending_intent = None

    elif detected_intent == "invoice":
        if extracted.get("is_quotation_conversion"):
            if not extracted.get("quotation_number"):
                missing_fields.append("quotation_number")
                detected_intent = "clarify"
                conv_state.pending_intent = "invoice"
            else:
                conv_state.pending_intent = None
        else:
            if not extracted.get("customer_name"):
                missing_fields.append("customer_name")
            if not extracted.get("line_items"):
                missing_fields.append("line_items")
            elif _items_missing_quantity(extracted):
                missing_fields.append("quantity")
            if missing_fields:
                detected_intent = "clarify"
                conv_state.pending_intent = "invoice"
            else:
                conv_state.pending_intent = None
    else:
        # Clear pending if they switched topics to catalog or off-topic
        conv_state.pending_intent = None

    # Persist state only while a workflow is waiting on the user.
    if conv_state.pending_intent:
        await conversation_store.save(conv_state, session)
    else:
        await conversation_store.clear(conv_state.conversation_id, session)

    response_text = ""
    if detected_intent == "clarify":
        if "customer_name" in missing_fields and "line_items" in missing_fields:
            response_text = (
                "I'd be happy to help! To get started, I need:\n"
                "1. **Customer name** — who is this for?\n"
                "2. **Items + quantities** — what would you like to include?\n\n"
                "Example: _Create a quotation for Ramesh Traders, 10 kg TMT Steel Rod 12mm_"
            )
        elif "customer_name" in missing_fields:
            response_text = "Which customer should this document be prepared for?"
        elif "line_items" in missing_fields:
            if extracted.get("customer_name"):
                response_text = f"Which items and quantities should be included for **{extracted.get('customer_name')}**?"
            else:
                response_text = "Which items and quantities should be included?"
        elif "quantity" in missing_fields:
            names = _items_missing_quantity(extracted)
            if len(names) == 1:
                response_text = f"How many **{names[0]}** should I include?"
            else:
                listed = ", ".join(f"**{n}**" for n in names)
                response_text = f"Please tell me the quantity for each item: {listed}. Example: _10 {names[0]}_"
        elif "quotation_number" in missing_fields:
            response_text = "Please provide the quotation number you wish to convert (e.g. Q-202608-001)."
        else:
            response_text = res.clarification_question or "Could you please clarify your request?"

    return {
        "detected_intent": detected_intent,
        "extracted_entities": extracted,
        "missing_fields": missing_fields,
        "confidence": res.confidence,
        "response_text": response_text,
    }


def route_by_intent(state: AgentState) -> str:
    """Conditional edge router based on detected intent."""
    intent = state.get("detected_intent", "clarify")
    if intent == "quotation":
        return "quotation_agent"
    elif intent == "invoice":
        return "invoice_agent"
    elif intent == "catalog_query":
        return "catalog_agent"
    elif intent in ("out_of_scope", "off_topic", "future_feature"):
        return "out_of_scope_agent"
    return "clarify_agent"


async def quotation_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Handles Quotation creation via ToolRegistry."""
    from app.tools.registry import registry
    from app.errors.categories import InsufficientInformationError, MunimError
    
    context = config["configurable"]["request_context"]
    entities = state.get("extracted_entities", {})
    
    tool = registry.get("create_quotation")
    args = {
        "customer_name": entities.get("customer_name") or "",
        "line_items": entities.get("line_items") or []
    }
    
    async with _get_session(config) as session:
        try:
            result = await tool.invoke(args, context, session)
            data = result.data
            
            from app.conversation.store import conversation_store
            await conversation_store.clear(context.conversation_id, session)
            
            return {
                "response_text": data["response_text"],
                "document_type": "quotation",
                "document_id": data["quotation_id"],
                "document_number": data["quotation_number"],
                "pdf_url": data["pdf_url"],
                "response_attachments": [{"type": "pdf", "url": data["pdf_url"]}],
                "data": data,
            }
        except InsufficientInformationError as err:
            is_fuzzy = "fuzzy" in err.detail.lower()
            return {
                "response_text": err.user_message,
                "document_type": None,
                "requires_confirmation": is_fuzzy,
                "customer_match_pending": is_fuzzy,
            }
        except MunimError as err:
            return {"response_text": err.user_message, "document_type": None}


async def invoice_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Handles Tax Invoice creation via ToolRegistry."""
    from app.tools.registry import registry
    from app.errors.categories import InsufficientInformationError, MunimError
    
    context = config["configurable"]["request_context"]
    entities = state.get("extracted_entities", {})
    
    async with _get_session(config) as session:
        try:
            if entities.get("is_quotation_conversion"):
                tool = registry.get("convert_quotation")
                args = {"quotation_number": entities.get("quotation_number") or ""}
            else:
                tool = registry.get("create_invoice")
                args = {
                    "customer_name": entities.get("customer_name") or "",
                    "line_items": entities.get("line_items") or []
                }
            
            result = await tool.invoke(args, context, session)
            data = result.data

            from app.conversation.store import conversation_store
            await conversation_store.clear(context.conversation_id, session)

            return {
                "response_text": data["response_text"],
                "document_type": "invoice",
                "document_id": data["invoice_id"],
                "document_number": data["invoice_number"],
                "pdf_url": data["pdf_url"],
                "response_attachments": [{"type": "pdf", "url": data["pdf_url"]}],
                "data": data,
            }
        except InsufficientInformationError as err:
            return {"response_text": err.user_message, "document_type": None, "requires_confirmation": "fuzzy" in err.detail.lower()}
        except MunimError as err:
            return {"response_text": err.user_message, "document_type": None}

async def catalog_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Handles read-only catalog queries via ToolRegistry."""
    from app.tools.registry import registry
    from app.errors.categories import MunimError
    
    context = config["configurable"]["request_context"]
    entities = state.get("extracted_entities", {})
    item_query = entities.get("catalog_item_name")
    
    tool = registry.get("search_products")
    args = {"item_name": item_query}
    
    async with _get_session(config) as session:
        try:
            result = await tool.invoke(args, context, session)
            return {
                "response_text": result.data["response_text"],
                "document_type": None,
                "data": result.data,
            }
        except MunimError as err:
            return {"response_text": err.user_message, "document_type": None}


async def clarify_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node: Handles clarification responses."""
    resp = state.get("response_text") or "Could you please provide more details for your quotation or invoice request?"
    return {"response_text": resp}


async def out_of_scope_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node: Handles future features and off-topic messages."""
    intent = state.get("detected_intent", "")
    if intent == "off_topic":
        return {
            "response_text": (
                "I'm Munim, your business assistant! I can help you with:\n"
                "• Creating **Quotations** for customers\n"
                "• Generating **GST Tax Invoices**\n"
                "• Converting quotations to invoices\n"
                "• Checking item **prices and stock**\n\n"
                "What would you like to do?"
            )
        }
    return {
        "response_text": (
            "This feature (dues reminders, accounting sync, reports) is coming soon! "
            "Right now I can create **Quotations**, **Tax Invoices**, and check your **catalog**."
        )
    }


async def log_conversation_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Records interaction into conversation_log table."""
    tenant_id = uuid.UUID(state["tenant_id"])
    channel = state.get("channel", "web")
    raw_message = state.get("raw_message", "")
    intent = state.get("detected_intent")
    request_context = (config or {}).get("configurable", {}).get("request_context")
    conversation_id = request_context.conversation_id if request_context else None
    # One explicit timestamp per turn; history readers order by
    # (created_at, direction) so 'inbound' always precedes 'outbound'.
    turn_time = datetime.now(timezone.utc)

    async with _get_session(config) as session:
        # Inbound message log
        inbound_log = ConversationLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            channel=channel,
            direction="inbound",
            created_at=turn_time,
            raw_message=raw_message,
            detected_intent=intent,
            agent_invoked=intent,
        )
        session.add(inbound_log)

        # Outbound response log
        outbound_log = ConversationLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            channel=channel,
            direction="outbound",
            created_at=turn_time,
            raw_message=state.get("response_text", ""),
            detected_intent=intent,
            agent_invoked=intent,
        )
        session.add(outbound_log)
        await session.flush()

    return {}


def create_agent_graph() -> Any:
    """Build and compile the LangGraph workflow graph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("quotation_agent", quotation_agent_node)
    workflow.add_node("invoice_agent", invoice_agent_node)
    workflow.add_node("catalog_agent", catalog_agent_node)
    workflow.add_node("clarify_agent", clarify_agent_node)
    workflow.add_node("out_of_scope_agent", out_of_scope_agent_node)
    workflow.add_node("log_conversation", log_conversation_node)

    workflow.set_entry_point("classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "quotation_agent": "quotation_agent",
            "invoice_agent": "invoice_agent",
            "catalog_agent": "catalog_agent",
            "clarify_agent": "clarify_agent",
            "out_of_scope_agent": "out_of_scope_agent",
        },
    )

    workflow.add_edge("quotation_agent", "log_conversation")
    workflow.add_edge("invoice_agent", "log_conversation")
    workflow.add_edge("catalog_agent", "log_conversation")
    workflow.add_edge("clarify_agent", "log_conversation")
    workflow.add_edge("out_of_scope_agent", "log_conversation")
    workflow.add_edge("log_conversation", END)

    return workflow.compile()


# Global compiled graph singleton
agent_graph = create_agent_graph()
