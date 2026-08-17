"""
M1M Sprint 1 Step 4 — Quotation and Invoice Agents Test Suite
===============================================================

Comprehensive integration and unit tests covering:
  - Intent classification & entity extraction
  - Customer & item lookup services
  - Deterministic Quotation creation and PDF generation
  - Direct Invoice creation, GST calculation, stock decrement, PDF generation
  - Invoice from Quotation conversion & status update
  - Stock validation, insufficient stock error & rollback safety
  - LangGraph workflow execution & conversation logging
  - Direct FastAPI endpoint verification (/api/v1/chat)
"""

import os
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.agent.graph import agent_graph
from app.config import get_settings
from app.main import app
from app.models.conversation_log import ConversationLog
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceLine
from app.models.item import Item
from app.models.quotation import Quotation, QuotationLine
from app.models.stock import Stock
from app.models.tenant import Tenant
from app.services.customer_lookup import lookup_customer
from app.services.doc_number import generate_invoice_number, generate_quotation_number
from app.services.intent_classifier import IntentClassificationResult, classify_intent_sync
from app.services.invoice_service import (
    InsufficientStockError,
    QuotationNotFoundError,
    convert_quotation_to_invoice,
    create_direct_invoice,
)
from app.services.item_lookup import lookup_item
from app.services.quotation_service import create_quotation


@pytest.fixture
def tenant_id_uuid():
    settings = get_settings()
    return uuid.UUID(settings.effective_sprint_tenant_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. INTENT CLASSIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_intent_quotation_classification():
    """Verify natural-language quotation request is classified correctly."""
    result = classify_intent_sync("Create a quotation for Ramesh Traders for 5 TMT steel rods")
    assert result.intent == "quotation"
    assert result.confidence >= 0.6
    assert result.customer_name is not None
    assert len(result.line_items) >= 1


def test_intent_invoice_classification():
    """Verify natural-language direct invoice request is classified correctly."""
    result = classify_intent_sync("Generate an invoice for Patel Constructions for 10 PVC pipes")
    assert result.intent == "invoice"
    assert result.confidence >= 0.6
    assert result.customer_name is not None
    assert len(result.line_items) >= 1


def test_intent_conversion_classification():
    """Verify quotation conversion request is classified as invoice with is_quotation_conversion."""
    result = classify_intent_sync("Convert quotation Q-202608-001 into an invoice")
    assert result.intent == "invoice"
    assert result.is_quotation_conversion is True
    assert result.quotation_number == "Q-202608-001" or "Q-202608-001" in str(result.quotation_number)


def test_intent_low_confidence_clarify():
    """Verify vague or incomplete input triggers clarification."""
    result = classify_intent_sync("Hello there, can you help me?")
    assert result.intent in ("clarify", "out_of_scope")


def test_intent_empty_input():
    """Verify empty input triggers clarification."""
    result = classify_intent_sync("")
    assert result.intent == "clarify"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LOOKUP SERVICES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_customer_lookup_exact(db_session, tenant_id_uuid):
    """Verify exact case-insensitive customer lookup."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "Ramesh Traders")
    assert cust is not None
    assert "Ramesh" in cust.name
    assert cust.tenant_id == tenant_id_uuid


@pytest.mark.asyncio
async def test_customer_lookup_fuzzy(db_session, tenant_id_uuid):
    """Verify fuzzy customer lookup with partial name."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "ramesh")
    assert cust is not None
    assert "Ramesh Traders" == cust.name


@pytest.mark.asyncio
async def test_customer_lookup_not_found(db_session, tenant_id_uuid):
    """Verify unknown customer returns None."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "NonExistentCustomerXYZ")
    assert cust is None


@pytest.mark.asyncio
async def test_item_lookup_exact(db_session, tenant_id_uuid):
    """Verify item catalog lookup."""
    item = await lookup_item(db_session, tenant_id_uuid, "TMT Steel Rod 12mm")
    assert item is not None
    assert "TMT Steel Rod" in item.name
    assert item.gst_rate_percent == Decimal("18.00")
    assert item.unit_price == Decimal("58.00")


@pytest.mark.asyncio
async def test_item_lookup_fuzzy(db_session, tenant_id_uuid):
    """Verify fuzzy item catalog lookup."""
    item = await lookup_item(db_session, tenant_id_uuid, "tmt steel rod")
    assert item is not None
    assert "TMT Steel Rod" in item.name


@pytest.mark.asyncio
async def test_item_lookup_not_found(db_session, tenant_id_uuid):
    """Verify unknown item returns None."""
    item = await lookup_item(db_session, tenant_id_uuid, "Quantum Computer Core")
    assert item is None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. QUOTATION AGENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_quotation_creation_single_item(db_session, tenant_id_uuid):
    """Verify single-line quotation creation, deterministic subtotal, and PDF."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "Ramesh Traders")
    item = await lookup_item(db_session, tenant_id_uuid, "TMT Steel Rod 12mm")
    assert cust and item

    qty = Decimal("10.00")
    expected_subtotal = item.unit_price * qty  # 58.00 * 10 = 580.00

    quote_data = await create_quotation(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item, qty)],
    )

    assert quote_data["quotation_number"].startswith("Q-")
    assert Decimal(str(quote_data["subtotal"])) == expected_subtotal
    assert quote_data["pdf_url"] is not None

    # Check DB records
    q_id = uuid.UUID(quote_data["quotation_id"])
    q_res = await db_session.execute(select(Quotation).where(Quotation.id == q_id))
    quotation = q_res.scalar_one()
    assert quotation.status == "draft"
    assert quotation.subtotal == expected_subtotal

    lines_res = await db_session.execute(select(QuotationLine).where(QuotationLine.quotation_id == q_id))
    lines = list(lines_res.scalars().all())
    assert len(lines) == 1
    assert lines[0].line_total == expected_subtotal


@pytest.mark.asyncio
async def test_quotation_creation_multi_item(db_session, tenant_id_uuid):
    """Verify multi-line quotation calculation."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "Ganesh Engineering Works")
    item1 = await lookup_item(db_session, tenant_id_uuid, "MS Steel Plate 6mm")
    item2 = await lookup_item(db_session, tenant_id_uuid, "MS Hex Bolt M12x50mm")
    assert cust and item1 and item2

    qty1 = Decimal("5.00")   # 72.00 * 5 = 360.00
    qty2 = Decimal("100.00") # 8.00 * 100 = 800.00
    expected_subtotal = Decimal("1160.00")

    quote_data = await create_quotation(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item1, qty1), (item2, qty2)],
    )

    assert Decimal(str(quote_data["subtotal"])) == expected_subtotal
    assert len(quote_data["lines"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INVOICE AGENT & GST TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_direct_invoice_intra_state(db_session, tenant_id_uuid):
    """
    Verify intra-state invoice (Maharashtra -> Maharashtra).
    Customer: Ramesh Traders (Maharashtra)
    Item: TMT Steel Rod (18% GST), unit_price 58.00, qty 10.
    Subtotal: 580.00
    Total GST (18%): 104.40
    CGST (9%): 52.20
    SGST (9%): 52.20
    IGST: 0.00
    Grand Total: 684.40
    """
    cust = await lookup_customer(db_session, tenant_id_uuid, "Ramesh Traders")
    item = await lookup_item(db_session, tenant_id_uuid, "TMT Steel Rod 12mm")
    assert cust and item
    assert cust.state.lower() == "maharashtra"

    # Get initial stock
    stock_res = await db_session.execute(select(Stock).where(Stock.item_id == item.id))
    initial_stock = stock_res.scalar_one().quantity_available

    qty = Decimal("10.00")
    inv_data = await create_direct_invoice(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item, qty)],
    )

    assert inv_data["invoice_number"].startswith("INV-")
    assert Decimal(str(inv_data["subtotal"])) == Decimal("580.00")
    assert Decimal(str(inv_data["cgst_amount"])) == Decimal("52.20")
    assert Decimal(str(inv_data["sgst_amount"])) == Decimal("52.20")
    assert Decimal(str(inv_data["igst_amount"])) == Decimal("0.00")
    assert Decimal(str(inv_data["total_tax"])) == Decimal("104.40")
    assert Decimal(str(inv_data["total_amount"])) == Decimal("684.40")

    # Verify stock decrement
    stock_res_after = await db_session.execute(select(Stock).where(Stock.item_id == item.id))
    after_stock = stock_res_after.scalar_one().quantity_available
    assert after_stock == initial_stock - qty


@pytest.mark.asyncio
async def test_direct_invoice_inter_state(db_session, tenant_id_uuid):
    """
    Verify inter-state invoice (Maharashtra -> Karnataka).
    Customer: Shri Ram Industries (Karnataka)
    Item: MS Steel Plate 6mm (18% GST), unit_price 72.00, qty 10.
    Subtotal: 720.00
    IGST (18%): 129.60
    CGST / SGST: 0.00
    Grand Total: 849.60
    """
    cust = await lookup_customer(db_session, tenant_id_uuid, "Shri Ram Industries")
    item = await lookup_item(db_session, tenant_id_uuid, "MS Steel Plate 6mm")
    assert cust and item
    assert cust.state.lower() == "karnataka"

    qty = Decimal("10.00")
    inv_data = await create_direct_invoice(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item, qty)],
    )

    assert Decimal(str(inv_data["subtotal"])) == Decimal("720.00")
    assert Decimal(str(inv_data["cgst_amount"])) == Decimal("0.00")
    assert Decimal(str(inv_data["sgst_amount"])) == Decimal("0.00")
    assert Decimal(str(inv_data["igst_amount"])) == Decimal("129.60")
    assert Decimal(str(inv_data["total_amount"])) == Decimal("849.60")


@pytest.mark.asyncio
async def test_insufficient_stock_prevents_invoice_and_stock_change(db_session, tenant_id_uuid):
    """Verify invoice fails when stock is insufficient, leaving stock untouched."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "Ramesh Traders")
    item = await lookup_item(db_session, tenant_id_uuid, "Chain Pulley Block 1 Ton")
    assert cust and item

    # Get current stock
    stock_res = await db_session.execute(select(Stock).where(Stock.item_id == item.id))
    stock_row = stock_res.scalar_one()
    current_available = stock_row.quantity_available

    excessive_qty = current_available + Decimal("100.00")

    with pytest.raises(InsufficientStockError):
        await create_direct_invoice(
            session=db_session,
            tenant_id=tenant_id_uuid,
            customer=cust,
            items_with_qty=[(item, excessive_qty)],
        )

    # Re-query stock to verify it is completely unchanged
    stock_res_check = await db_session.execute(select(Stock).where(Stock.item_id == item.id))
    assert stock_res_check.scalar_one().quantity_available == current_available


@pytest.mark.asyncio
async def test_convert_quotation_to_invoice(db_session, tenant_id_uuid):
    """Verify converting a quotation into an invoice."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "Patel Constructions")
    item = await lookup_item(db_session, tenant_id_uuid, "PVC Rigid Conduit Pipe 25mm")
    assert cust and item

    qty = Decimal("5.00")
    quote_data = await create_quotation(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item, qty)],
    )
    quote_num = quote_data["quotation_number"]

    # Convert quotation to invoice
    inv_data = await convert_quotation_to_invoice(
        session=db_session,
        tenant_id=tenant_id_uuid,
        quotation_identifier=quote_num,
    )

    assert inv_data["invoice_number"].startswith("INV-")
    assert inv_data["quotation_number"] == quote_num

    # Verify quotation is marked as 'converted'
    q_res = await db_session.execute(
        select(Quotation).where(Quotation.quotation_number == quote_num)
    )
    q_row = q_res.scalar_one()
    assert q_row.status == "converted"


@pytest.mark.asyncio
async def test_convert_already_converted_quotation_fails(db_session, tenant_id_uuid):
    """Verify converting an already converted quotation raises QuotationNotFoundError."""
    cust = await lookup_customer(db_session, tenant_id_uuid, "Patel Constructions")
    item = await lookup_item(db_session, tenant_id_uuid, "Safety Helmet IS:2925")
    assert cust and item

    quote_data = await create_quotation(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item, Decimal("2.00"))],
    )
    quote_num = quote_data["quotation_number"]

    # First conversion
    await convert_quotation_to_invoice(
        session=db_session,
        tenant_id=tenant_id_uuid,
        quotation_identifier=quote_num,
    )

    # Second conversion attempt must fail
    with pytest.raises(QuotationNotFoundError, match="already been converted"):
        await convert_quotation_to_invoice(
            session=db_session,
            tenant_id=tenant_id_uuid,
            quotation_identifier=quote_num,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. LANGGRAPH WORKFLOW & API TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_agent_graph_quotation_flow(db_session, tenant_id_uuid):
    """Verify end-to-end execution of quotation creation through the LangGraph agent."""
    initial_state = {
        "tenant_id": str(tenant_id_uuid),
        "user_id": None,
        "channel": "web",
        "raw_message": "Create a quotation for Ramesh Traders for 2 TMT Steel Rods",
    }
    config = {"configurable": {"session": db_session}}

    result = await agent_graph.ainvoke(initial_state, config=config)

    assert result.get("detected_intent") == "quotation"
    assert result.get("document_type") == "quotation"
    assert result.get("document_number", "").startswith("Q-")
    assert "Ramesh Traders" in result.get("response_text", "")

    # Check conversation log
    log_res = await db_session.execute(
        select(ConversationLog).where(ConversationLog.tenant_id == tenant_id_uuid)
    )
    logs = list(log_res.scalars().all())
    assert len(logs) >= 2


from app.api.v1.chat import get_db_session


@pytest.mark.asyncio
async def test_chat_api_endpoint_quotation(db_session):
    """Verify POST /api/v1/chat endpoint for quotation creation."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat",
                json={"message": "Create a quotation for Ramesh Traders for 2 TMT steel rods"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "quotation"
            assert data["document_type"] == "quotation"
            assert data["document_number"].startswith("Q-")
            assert data["pdf_url"] is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_api_endpoint_direct_invoice(db_session):
    """Verify POST /api/v1/chat endpoint for invoice creation."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat",
                json={"message": "Create an invoice for Ramesh Traders for 2 TMT steel rods"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "invoice"
            assert data["document_type"] == "invoice"
            assert data["document_number"].startswith("INV-")
    finally:
        app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DOCUMENT SERVING ROUTE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_document_serve_existing_pdf(db_session, tenant_id_uuid):
    """
    Verify GET /documents/{tenant_id}/{doc_type}/{filename} returns 200
    and application/pdf for a document that was just created via the quotation service.
    """
    from app.services.quotation_service import create_quotation
    from app.services.customer_lookup import lookup_customer
    from app.services.item_lookup import lookup_item

    cust = await lookup_customer(db_session, tenant_id_uuid, "Ramesh Traders")
    item = await lookup_item(db_session, tenant_id_uuid, "TMT Steel Rod 12mm")
    assert cust and item

    quote_data = await create_quotation(
        session=db_session,
        tenant_id=tenant_id_uuid,
        customer=cust,
        items_with_qty=[(item, Decimal("1.00"))],
    )

    pdf_url = quote_data["pdf_url"]  # e.g. /documents/{tenant_id}/quotations/Q-....pdf
    assert pdf_url is not None

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(pdf_url)
            assert response.status_code == 200, f"Expected 200, got {response.status_code} for {pdf_url}"
            assert response.headers["content-type"] == "application/pdf"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_document_serve_not_found(tenant_id_uuid):
    """Verify GET /documents/... returns 404 for a non-existent file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/documents/{tenant_id_uuid}/quotations/Q-DOES-NOT-EXIST.pdf"
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_document_serve_path_traversal_rejected(tenant_id_uuid):
    """Verify GET /documents/... rejects path traversal attempts with 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            f"/documents/{tenant_id_uuid}/quotations/..%2F..%2F..%2Fetc%2Fpasswd.pdf"
        )
        # FastAPI will either 400 (our guard) or 404 after path normalisation;
        # in both cases it must NOT return 200.
        assert response.status_code in (400, 404)
