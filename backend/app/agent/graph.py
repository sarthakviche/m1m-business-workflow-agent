"""
M1M (Munim.ai) — LangGraph Workflow Definition
================================================
Orchestrates intent classification, quotation agent, invoice agent,
and conversation logging.

Flow:
  START → classify_intent → [quotation_agent | invoice_agent | clarify_agent | out_of_scope_agent] → log_conversation → END
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
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
from app.services.customer_lookup import lookup_customer
from app.services.intent_classifier import classify_intent_sync
from app.services.invoice_service import (
    InsufficientStockError,
    QuotationNotFoundError,
    convert_quotation_to_invoice,
    create_direct_invoice,
)
from app.services.item_lookup import lookup_item
from app.services.quotation_service import create_quotation


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


async def classify_intent_node(state: AgentState) -> Dict[str, Any]:
    """Node: Classifies user message intent and extracts structured entities."""
    raw_message = state.get("raw_message", "")
    res = classify_intent_sync(raw_message)

    extracted = {
        "customer_name": res.customer_name,
        "line_items": [i.model_dump() for i in res.line_items],
        "quotation_number": res.quotation_number,
        "is_quotation_conversion": res.is_quotation_conversion,
    }

    missing_fields: List[str] = []
    detected_intent = res.intent

    if detected_intent == "quotation":
        if not res.customer_name:
            missing_fields.append("customer_name")
        if not res.line_items:
            missing_fields.append("line_items")
        if missing_fields:
            detected_intent = "clarify"

    elif detected_intent == "invoice":
        if res.is_quotation_conversion:
            if not res.quotation_number:
                missing_fields.append("quotation_number")
                detected_intent = "clarify"
        else:
            if not res.customer_name:
                missing_fields.append("customer_name")
            if not res.line_items:
                missing_fields.append("line_items")
            if missing_fields:
                detected_intent = "clarify"

    response_text = ""
    if detected_intent == "clarify":
        if "customer_name" in missing_fields and "line_items" in missing_fields:
            response_text = "Please specify the customer name and the items/quantities you would like to include."
        elif "customer_name" in missing_fields:
            response_text = "Which customer should this document be prepared for?"
        elif "line_items" in missing_fields:
            response_text = f"Which items and quantities should be billed for **{res.customer_name}**?"
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
    elif intent == "out_of_scope":
        return "out_of_scope_agent"
    return "clarify_agent"


async def quotation_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Handles Quotation creation deterministically."""
    tenant_id = uuid.UUID(state["tenant_id"])
    entities = state.get("extracted_entities", {})

    async with _get_session(config) as session:
        cust_name = entities.get("customer_name")
        customer = await lookup_customer(session, tenant_id, cust_name)
        if not customer:
            return {
                "response_text": f"Customer **'{cust_name}'** was not found in your customer directory. Please check the spelling or add them first.",
                "document_type": None,
            }

        raw_items = entities.get("line_items", [])
        resolved_items: List[Tuple[Item, Decimal]] = []

        for item_data in raw_items:
            i_name = item_data.get("item_name", "")
            qty = Decimal(str(item_data.get("quantity", 1.0)))
            item = await lookup_item(session, tenant_id, i_name)
            if not item:
                return {
                    "response_text": f"Item **'{i_name}'** was not found in your catalog. Please check the item name.",
                    "document_type": None,
                }
            resolved_items.append((item, qty))

        # Create quotation
        result = await create_quotation(session, tenant_id, customer, resolved_items)

        return {
            "response_text": result["response_text"],
            "document_type": "quotation",
            "document_id": result["quotation_id"],
            "document_number": result["quotation_number"],
            "pdf_url": result["pdf_url"],
            "response_attachments": [{"type": "pdf", "url": result["pdf_url"]}],
            "data": result,
        }


async def invoice_agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Handles Tax Invoice creation (direct and quotation conversion)."""
    tenant_id = uuid.UUID(state["tenant_id"])
    entities = state.get("extracted_entities", {})

    async with _get_session(config) as session:
        # Flow B: Quotation Conversion
        if entities.get("is_quotation_conversion"):
            q_num = entities.get("quotation_number") or ""
            try:
                result = await convert_quotation_to_invoice(session, tenant_id, q_num)
                return {
                    "response_text": result["response_text"],
                    "document_type": "invoice",
                    "document_id": result["invoice_id"],
                    "document_number": result["invoice_number"],
                    "pdf_url": result["pdf_url"],
                    "response_attachments": [{"type": "pdf", "url": result["pdf_url"]}],
                    "data": result,
                }
            except (QuotationNotFoundError, InsufficientStockError, ValueError) as err:
                return {
                    "response_text": f"Cannot convert quotation: {str(err)}",
                    "document_type": None,
                }

        # Flow A: Direct Invoice
        cust_name = entities.get("customer_name")
        customer = await lookup_customer(session, tenant_id, cust_name)
        if not customer:
            return {
                "response_text": f"Customer **'{cust_name}'** was not found in your customer directory.",
                "document_type": None,
            }

        raw_items = entities.get("line_items", [])
        resolved_items: List[Tuple[Item, Decimal]] = []

        for item_data in raw_items:
            i_name = item_data.get("item_name", "")
            qty = Decimal(str(item_data.get("quantity", 1.0)))
            item = await lookup_item(session, tenant_id, i_name)
            if not item:
                return {
                    "response_text": f"Item **'{i_name}'** was not found in your catalog.",
                    "document_type": None,
                }
            resolved_items.append((item, qty))

        try:
            result = await create_direct_invoice(session, tenant_id, customer, resolved_items)
            return {
                "response_text": result["response_text"],
                "document_type": "invoice",
                "document_id": result["invoice_id"],
                "document_number": result["invoice_number"],
                "pdf_url": result["pdf_url"],
                "response_attachments": [{"type": "pdf", "url": result["pdf_url"]}],
                "data": result,
            }
        except InsufficientStockError as err:
            return {
                "response_text": f"⚠️ **Invoice creation failed:** {str(err)} No invoice was created and stock remains unchanged.",
                "document_type": None,
            }
        except Exception as err:
            return {
                "response_text": f"⚠️ **Invoice creation error:** {str(err)}",
                "document_type": None,
            }


async def clarify_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node: Handles clarification responses."""
    resp = state.get("response_text") or "Could you please provide more details for your quotation or invoice request?"
    return {"response_text": resp}


async def out_of_scope_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node: Informs user that requested feature is out of Sprint 1 scope."""
    return {
        "response_text": (
            "This capability (dues reminders, stock queries, accounting sync) is part of a future sprint. "
            "Currently in Sprint 1, I can create **Quotations**, generate **Tax Invoices**, and **convert Quotations into Invoices**."
        )
    }


async def log_conversation_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node: Records interaction into conversation_log table."""
    tenant_id = uuid.UUID(state["tenant_id"])
    channel = state.get("channel", "web")
    raw_message = state.get("raw_message", "")
    intent = state.get("detected_intent")

    async with _get_session(config) as session:
        # Inbound message log
        inbound_log = ConversationLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            channel=channel,
            direction="inbound",
            raw_message=raw_message,
            detected_intent=intent,
            agent_invoked=intent,
        )
        session.add(inbound_log)

        # Outbound response log
        outbound_log = ConversationLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            channel=channel,
            direction="outbound",
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
            "clarify_agent": "clarify_agent",
            "out_of_scope_agent": "out_of_scope_agent",
        },
    )

    workflow.add_edge("quotation_agent", "log_conversation")
    workflow.add_edge("invoice_agent", "log_conversation")
    workflow.add_edge("clarify_agent", "log_conversation")
    workflow.add_edge("out_of_scope_agent", "log_conversation")
    workflow.add_edge("log_conversation", END)

    return workflow.compile()


# Global compiled graph singleton
agent_graph = create_agent_graph()
