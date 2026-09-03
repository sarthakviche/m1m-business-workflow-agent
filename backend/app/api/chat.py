"""
chat.py — /chat/message route with Gemini agent & deterministic fallback.
"""

from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db, set_tenant_context
from app.models.user import AppUser
from app.models.customer import Customer
from app.models.item import Item
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.payment import Payment

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    phone: str = "9876543210"


class ChatMessageResponse(BaseModel):
    reply: str
    mode: str  # "llm" or "fallback"
    intent: str
    data: Any | None = None


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Copilot Chat endpoint.
    Attempts primary LLM processing, falling back to deterministic database query engine if LLM is unavailable or fails.
    """
    phone = body.phone
    message_text = body.message.strip()

    # 1. Resolve user and tenant context
    res_user = await db.execute(select(AppUser).where(AppUser.phone == phone))
    user = res_user.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    await set_tenant_context(db, user.tenant_id)
    tenant_id = user.tenant_id

    # 2. Try primary Gemini LLM if key is configured
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = (
                f"You are Munim.ai, an AI copilot for Indian SMEs. "
                f"User asked: '{message_text}'. Provide a concise, helpful response."
            )
            llm_res = model.generate_content(prompt)
            if llm_res and llm_res.text:
                return ChatMessageResponse(
                    reply=llm_res.text,
                    mode="llm",
                    intent="general_llm",
                    data=None
                )
        except Exception:
            # Fall through seamlessly to deterministic fallback path
            pass

    # 3. Deterministic DB Fallback Engine
    msg_lower = message_text.lower()

    # Intent A: Customer retrieval
    if "customer" in msg_lower:
        if "find" in msg_lower or "search" in msg_lower or "test customer" in msg_lower:
            query_str = msg_lower.replace("find customer", "").replace("find", "").replace("search", "").strip()
            res = await db.execute(
                select(Customer).where(
                    Customer.tenant_id == tenant_id,
                    Customer.name.ilike(f"%{query_str}%")
                )
            )
            customers = res.scalars().all()
            if not customers:
                res_all = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
                customers = res_all.scalars().all()
            
            cust_list_str = "\n".join([f"• {c.name} ({c.phone or 'No phone'}, State: {c.state or 'N/A'})" for c in customers])
            return ChatMessageResponse(
                reply=f"Found {len(customers)} matching customer(s):\n{cust_list_str}",
                mode="fallback",
                intent="customer_search",
                data=[{"id": str(c.id), "name": c.name, "phone": c.phone} for c in customers]
            )
        else:
            res = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
            customers = res.scalars().all()
            cust_list_str = "\n".join([f"• {c.name} - {c.phone or 'N/A'}" for c in customers])
            return ChatMessageResponse(
                reply=f"You have {len(customers)} customer(s) registered:\n{cust_list_str}",
                mode="fallback",
                intent="customer_list",
                data=[{"id": str(c.id), "name": c.name, "phone": c.phone} for c in customers]
            )

    # Intent B: Item / Stock retrieval
    if "item" in msg_lower or "stock" in msg_lower or "product" in msg_lower:
        res = await db.execute(select(Item).where(Item.tenant_id == tenant_id))
        items = res.scalars().all()
        items_str = "\n".join([f"• {it.name}: ₹{float(it.unit_price):,.2f} ({it.gst_rate_percent}% GST)" for it in items])
        return ChatMessageResponse(
            reply=f"Here is your catalog items list ({len(items)} items):\n{items_str}",
            mode="fallback",
            intent="item_list",
            data=[{"id": str(it.id), "name": it.name, "price": float(it.unit_price)} for it in items]
        )

    # Intent C: Dues / Outstanding calculation
    if "outstanding" in msg_lower or "dues" in msg_lower or "how much money" in msg_lower:
        res_inv = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant_id))
        invoices = res_inv.scalars().all()
        total_invoiced = sum((inv.total_amount or Decimal("0") for inv in invoices), Decimal("0"))
        
        res_pay = await db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.tenant_id == tenant_id))
        total_paid = Decimal(str(res_pay.scalar() or 0))
        outstanding = total_invoiced - total_paid

        return ChatMessageResponse(
            reply=f"💰 Total Invoiced: ₹{float(total_invoiced):,.2f}\n"
                  f"✅ Total Received: ₹{float(total_paid):,.2f}\n"
                  f"⚠️ Current Outstanding Dues: ₹{float(outstanding):,.2f}",
            mode="fallback",
            intent="dues_summary",
            data={"total_invoiced": float(total_invoiced), "total_paid": float(total_paid), "outstanding": float(outstanding)}
        )

    # Intent D: Specific Invoice search (e.g., INV-002)
    if "inv-" in msg_lower or "invoice inv" in msg_lower:
        words = message_text.split()
        inv_num = next((w for w in words if "inv-" in w.lower()), "INV-002").upper()
        res_inv = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_number.ilike(f"%{inv_num}%")
            )
        )
        invoice = res_inv.scalar_one_or_none()
        if invoice:
            res_c = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
            customer = res_c.scalar_one_or_none()
            return ChatMessageResponse(
                reply=f"📄 Invoice #{invoice.invoice_number} Details:\n"
                      f"Customer: {customer.name if customer else 'Unknown'}\n"
                      f"Total Amount: ₹{float(invoice.total_amount or 0):,.2f}\n"
                      f"Status: {invoice.status.upper()}\n"
                      f"Due Date: {invoice.due_date or 'N/A'}",
                mode="fallback",
                intent="invoice_detail",
                data={"id": str(invoice.id), "invoice_number": invoice.invoice_number, "total_amount": float(invoice.total_amount or 0)}
            )

    # Intent E: Invoices list / status filter
    if "invoice" in msg_lower:
        query_status = None
        if "unpaid" in msg_lower:
            query_status = "unpaid"
        elif "paid" in msg_lower:
            query_status = "paid"
        elif "overdue" in msg_lower:
            query_status = "overdue"

        res_inv = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant_id))
        invoices = res_inv.scalars().all()

        if query_status == "unpaid":
            invoices = [i for i in invoices if i.status == "unpaid"]
        elif query_status == "paid":
            invoices = [i for i in invoices if i.status == "paid"]

        inv_str_list = []
        for inv in invoices:
            res_c = await db.execute(select(Customer).where(Customer.id == inv.customer_id))
            cust = res_c.scalar_one_or_none()
            inv_str_list.append(f"• #{inv.invoice_number} | {cust.name if cust else 'Cust'} | ₹{float(inv.total_amount or 0):,.2f} | Status: {inv.status}")

        inv_summary = "\n".join(inv_str_list) if inv_str_list else "No matching invoices found."
        return ChatMessageResponse(
            reply=f"Found {len(invoices)} invoice(s):\n{inv_summary}",
            mode="fallback",
            intent="invoice_list",
            data=[{"id": str(i.id), "number": i.invoice_number, "amount": float(i.total_amount or 0)} for i in invoices]
        )

    # Intent F: Quotations list
    if "quotation" in msg_lower:
        res_q = await db.execute(select(Quotation).where(Quotation.tenant_id == tenant_id))
        quotations = res_q.scalars().all()
        q_str_list = []
        for q in quotations:
            res_c = await db.execute(select(Customer).where(Customer.id == q.customer_id))
            cust = res_c.scalar_one_or_none()
            q_str_list.append(f"• Quotation #{q.quotation_number} | {cust.name if cust else 'Cust'} | Subtotal: ₹{float(q.subtotal or 0):,.2f}")
        
        q_summary = "\n".join(q_str_list) if q_str_list else "No quotations found."
        return ChatMessageResponse(
            reply=f"Found {len(quotations)} quotation(s):\n{q_summary}",
            mode="fallback",
            intent="quotation_list",
            data=[{"id": str(q.id), "number": q.quotation_number, "subtotal": float(q.subtotal or 0)} for q in quotations]
        )

    # Intent G: PDF generation command
    if "pdf" in msg_lower or "generate" in msg_lower:
        return ChatMessageResponse(
            reply="📄 You can download official PDF invoices and quotations directly from the Documents tab or by invoking the /invoices/{id}/pdf and /quotations/{id}/pdf endpoints.",
            mode="fallback",
            intent="pdf_info",
            data=None
        )

    # Fallback default: Unsupported / general inquiry response
    return ChatMessageResponse(
        reply="I am your M1M Business Copilot. I can help you with:\n"
              "• Customers ('show my customers', 'find customer Test Customer 2')\n"
              "• Items ('show my items')\n"
              "• Invoices ('show invoices', 'show unpaid invoices', 'show invoice INV-002')\n"
              "• Quotations ('show my quotations')\n"
              "• Dues & Outstanding ('how much money is outstanding?')\n"
              "• PDF Generation ('generate invoice pdf')",
        mode="fallback",
        intent="unsupported_help",
        data=None
    )
