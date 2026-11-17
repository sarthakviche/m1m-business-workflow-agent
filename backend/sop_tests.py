"""
SOP Happy-Path + Edge Case Tests for M1M Chat Agent
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import httpx
import json

BASE = "http://localhost:8000/api/v1/chat"
DOCS = "http://localhost:8000/api/v1/documents"

def chat(message: str, history: list = None) -> dict:
    r = httpx.post(BASE, json={"message": message, "conversation_history": history or []}, timeout=30)
    r.raise_for_status()
    return r.json()

def sep(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def show(label: str, resp: dict):
    print(f"\n[{label}]")
    print(f"  intent  : {resp.get('intent', resp.get('detected_intent', '?'))}")
    print(f"  doc_type: {resp.get('document_type', '-')}")
    print(f"  pdf_url : {resp.get('pdf_url', '-')}")
    print(f"  response: {resp.get('response_text', '')[:120]}")

# ── TEST 1: Happy path — one-shot quotation ──────────────────────────────────
sep("TEST 1: One-shot quotation (customer + items in one message)")
r = chat("Create a quotation for Ramesh Traders, 10 kg TMT Steel Rod 12mm and 50 pcs MS Hex Bolt M12x50mm")
show("T1 one-shot", r)

# ── TEST 2: Multi-turn — customer first, items second ─────────────────────────
sep("TEST 2: Multi-turn quotation (customer only -> then items)")
r1 = chat("Create a quotation for Ganesh Engineering Works")
show("T2a customer-only", r1)

history2 = [
    {"role": "user", "content": "Create a quotation for Ganesh Engineering Works"},
    {"role": "assistant", "content": r1.get("response_text", "")},
]
r2 = chat("20 kg TMT Steel Rod 12mm and 100 pcs MS Hex Bolt M12x50mm", history2)
show("T2b items reply", r2)

# ── TEST 3: Item NOT in catalog — should show catalog, not hallucinate ────────
sep("TEST 3: Item not in catalog (should ask user to pick from catalog)")
r = chat("Create a quotation for Ramesh Traders, 5 units LED Bulbs")
show("T3 unknown-item", r)

# ── TEST 4: Context switch mid-conversation ───────────────────────────────────
sep("TEST 4: Context switch (start quotation, then ask for invoice)")
r1 = chat("I want a quotation for Patel Constructions")
show("T4a start-quotation", r1)

history4 = [
    {"role": "user", "content": "I want a quotation for Patel Constructions"},
    {"role": "assistant", "content": r1.get("response_text", "")},
]
r2 = chat("Actually make it an invoice instead", history4)
show("T4b switch-to-invoice", r2)

# ── TEST 5: Off-topic message ─────────────────────────────────────────────────
sep("TEST 5: Off-topic message")
r = chat("Tell me a joke")
show("T5 off-topic", r)

# ── TEST 6: Quotation → Invoice conversion ────────────────────────────────────
sep("TEST 6: Convert existing quotation to invoice")
docs = httpx.get(DOCS, timeout=10).json()
q_docs = [d for d in docs.get("documents", []) if d["document_type"] == "quotation"]
if q_docs:
    q_num = q_docs[0]["document_number"]
    r = chat(f"Convert quotation {q_num} to an invoice")
    show(f"T6 convert {q_num}", r)
else:
    print("  [SKIP] No quotations in DB")

# ── TEST 7: Catalog query ─────────────────────────────────────────────────────
sep("TEST 7: Catalog query — what items do we have?")
r = chat("Show me all items in our catalog")
show("T7 catalog-list", r)

sep("TEST 7b: Price of specific item")
r = chat("What is the price of TMT Steel Rod 12mm?")
show("T7b price-query", r)

# ── TEST 8: No customer name — should ask for customer ───────────────────────
sep("TEST 8: No customer name (should ask 'which customer?')")
r = chat("Create a quotation for 5 kg TMT Steel Rod 12mm")
show("T8 no-customer", r)

# ── SUMMARY ───────────────────────────────────────────────────────────────────
sep("DONE — Review outputs above")
