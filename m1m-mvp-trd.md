# TRD — M1M (Munim.ai) MVP
### Technical Requirements Document — Implementation Context for Coding Agent
**Companion to:** `m1m-mvp-prd.md` (product scope, user flows, why-decisions). This document is the *how* — read the PRD first for the *what* and *why*; this document assumes it and does not re-justify product decisions.

**Ground rules for whoever/whatever implements this:**
- Do not add features beyond the four locked in the PRD (Quotation, Invoice, Dues, Stock) plus onboarding/auth/dashboard scaffolding described here.
- GST/tax math is never an LLM call — it is a pure, unit-tested function. This is non-negotiable, not a style preference.
- Every tenant-scoped table has Row-Level Security enabled — no query path should be able to read cross-tenant data even by accident.
- Every write action goes through the `conversation_log` / `audit_log` — no silent writes.

---

## 1. Repository Structure

```
m1m/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app entrypoint
│   │   ├── config.py                    # env-driven settings (pydantic-settings)
│   │   ├── api/
│   │   │   ├── auth.py                  # /auth/* routes
│   │   │   ├── onboarding.py            # /onboarding/* routes
│   │   │   ├── chat.py                  # /chat/* routes
│   │   │   ├── documents.py             # /documents/* routes
│   │   │   ├── customers.py             # /customers/* routes
│   │   │   ├── items.py                 # /items/* routes
│   │   │   ├── dashboard.py             # /dashboard/* routes
│   │   │   └── whatsapp_webhook.py      # /webhooks/whatsapp
│   │   ├── agents/
│   │   │   ├── graph.py                 # LangGraph StateGraph definition
│   │   │   ├── state.py                 # AgentState TypedDict
│   │   │   ├── router.py                # intent classification node
│   │   │   ├── quotation_agent.py
│   │   │   ├── invoice_agent.py
│   │   │   ├── dues_agent.py
│   │   │   ├── stock_agent.py
│   │   │   └── tools/
│   │   │       ├── customer_tools.py    # lookup/create customer
│   │   │       ├── item_tools.py        # lookup item
│   │   │       ├── quotation_tools.py
│   │   │       ├── invoice_tools.py
│   │   │       ├── stock_tools.py
│   │   │       └── payment_tools.py
│   │   ├── services/
│   │   │   ├── gst_calculator.py        # pure deterministic tax logic
│   │   │   ├── pdf_service.py           # WeasyPrint rendering
│   │   │   ├── csv_validator.py         # onboarding bulk-upload validation
│   │   │   ├── whatsapp_client.py       # Meta Cloud API wrapper
│   │   │   └── otp_service.py
│   │   ├── models/                      # SQLAlchemy ORM models (mirrors schema in Section 4)
│   │   ├── schemas/                     # Pydantic request/response models
│   │   ├── db/
│   │   │   ├── session.py               # async session factory, RLS context setter
│   │   │   └── migrations/              # Alembic migrations
│   │   └── templates/
│   │       ├── quotation.html           # Jinja2 → WeasyPrint
│   │       └── invoice.html
│   ├── tests/
│   │   ├── unit/                        # gst_calculator, csv_validator, tools
│   │   ├── integration/                 # API endpoint tests
│   │   └── fixtures/
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Onboarding/
│   │   │   │   ├── BusinessProfile.tsx
│   │   │   │   ├── CatalogChoice.tsx
│   │   │   │   ├── ManualItemEntry.tsx
│   │   │   │   ├── BulkUpload.tsx
│   │   │   │   └── OnboardingComplete.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Chat.tsx
│   │   │   ├── Documents.tsx
│   │   │   ├── Customers.tsx
│   │   │   ├── Inventory.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/
│   │   ├── api/                         # typed fetch wrappers per endpoint
│   │   ├── state/                       # auth/session context
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── .env.example
└── docker-compose.yml                   # local Postgres + backend for dev
```

---

## 2. Tech Stack & Versions

| Layer | Choice | Version (pin these) |
|---|---|---|
| Backend language/runtime | Python | 3.11+ |
| Web framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Agent orchestration | LangGraph | 0.2+ |
| LLM SDK | `google-generativeai` (Gemini) or `anthropic` — pick one, don't mix providers in MVP | latest stable |
| PDF | WeasyPrint | 62+ |
| Templating | Jinja2 | 3.1+ |
| CSV/data validation | Pandas + Pydantic | pandas 2.x, pydantic 2.x |
| Database | PostgreSQL via Supabase | 15+ |
| Frontend | React + TypeScript | React 18, TS 5 |
| Build tool | Vite | 5+ |
| Styling | Tailwind CSS | 3+ |
| HTTP client (frontend) | fetch + a thin typed wrapper (no heavy client lib needed for MVP scope) | — |
| WhatsApp | Meta Cloud API (Graph API v20.0+) | — |
| Tunnel (dev only) | ngrok | — |

---

## 3. Environment Configuration

`.env.example` (backend):
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/m1m
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
LLM_PROVIDER=gemini              # or "anthropic"
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
WHATSAPP_CLOUD_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=           # arbitrary string set during Meta webhook config
JWT_SECRET=                      # for session tokens post-OTP
OTP_PROVIDER=whatsapp            # send OTP via WhatsApp template message, no separate SMS vendor needed for MVP
ENV=development                  # development | production
```

**Secrets handling:** never commit `.env`. For local dev, `.env` is gitignored and loaded via `pydantic-settings`. For any deployed environment, use the hosting platform's secret manager (Supabase project secrets / Railway/Fly env vars) — not a checked-in file.

---

## 4. Database Schema (implementation-ready DDL)

Extends the schema already given in the PRD with indexes, constraints, and RLS policies made explicit for the implementer.

```sql
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE tenant (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name TEXT NOT NULL,
    gstin TEXT,
    state TEXT NOT NULL,
    address TEXT,
    logo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE app_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    phone TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner','staff','accountant')),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_app_user_tenant ON app_user(tenant_id);

CREATE TABLE customer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT,
    gstin TEXT,
    state TEXT,
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_customer_tenant ON customer(tenant_id);
CREATE INDEX idx_customer_name_trgm ON customer USING gin (name gin_trgm_ops); -- requires pg_trgm, for fuzzy match

CREATE TABLE item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    hsn_code TEXT,
    gst_rate_percent NUMERIC(5,2) NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    unit TEXT DEFAULT 'pcs',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_item_tenant ON item(tenant_id);
CREATE INDEX idx_item_name_trgm ON item USING gin (name gin_trgm_ops);

CREATE TABLE stock (
    item_id UUID PRIMARY KEY REFERENCES item(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    quantity_available NUMERIC(12,2) NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE quotation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customer(id),
    quotation_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','converted')),
    subtotal NUMERIC(14,2),
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, quotation_number)
);

CREATE TABLE quotation_line (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id UUID NOT NULL REFERENCES quotation(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES item(id),
    quantity NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    line_total NUMERIC(14,2) NOT NULL
);

CREATE TABLE invoice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customer(id),
    quotation_id UUID REFERENCES quotation(id),
    invoice_number TEXT NOT NULL,
    subtotal NUMERIC(14,2),
    cgst_amount NUMERIC(14,2) DEFAULT 0,
    sgst_amount NUMERIC(14,2) DEFAULT 0,
    igst_amount NUMERIC(14,2) DEFAULT 0,
    total_amount NUMERIC(14,2),
    status TEXT NOT NULL DEFAULT 'unpaid' CHECK (status IN ('unpaid','partially_paid','paid')),
    due_date DATE,
    pdf_url TEXT,
    tally_push_status TEXT DEFAULT 'not_applicable' CHECK (tally_push_status IN ('not_applicable','pending','pushed')),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, invoice_number)
);
CREATE INDEX idx_invoice_tenant_status ON invoice(tenant_id, status);
CREATE INDEX idx_invoice_due_date ON invoice(due_date) WHERE status != 'paid';

CREATE TABLE invoice_line (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES item(id),
    quantity NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    gst_rate_percent NUMERIC(5,2) NOT NULL,
    line_total NUMERIC(14,2) NOT NULL
);

CREATE TABLE payment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
    amount NUMERIC(14,2) NOT NULL,
    method TEXT CHECK (method IN ('upi','cash','bank_transfer')),
    paid_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('whatsapp','web')),
    direction TEXT NOT NULL CHECK (direction IN ('inbound','outbound')),
    raw_message TEXT,
    detected_intent TEXT,
    agent_invoked TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_convlog_tenant_time ON conversation_log(tenant_id, created_at DESC);

CREATE TABLE tally_connection (
    tenant_id UUID PRIMARY KEY REFERENCES tenant(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'not_connected' CHECK (status IN ('not_connected','connected')),
    mode TEXT DEFAULT 'read_only',
    last_synced_at TIMESTAMPTZ
);

CREATE TABLE external_id_map (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    internal_entity_type TEXT NOT NULL,
    internal_id UUID NOT NULL,
    external_system TEXT NOT NULL,
    external_id TEXT NOT NULL
);

-- === Row-Level Security ===
-- Applied identically to every tenant-scoped table. Pattern shown once; repeat per table.
ALTER TABLE customer ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_customer ON customer
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
-- Repeat ALTER TABLE ... ENABLE ROW LEVEL SECURITY + CREATE POLICY for:
-- app_user, item, stock, quotation, quotation_line, invoice, invoice_line,
-- payment, conversation_log, tally_connection, external_id_map
-- (quotation_line/invoice_line have no direct tenant_id — join-scope via parent, or
--  denormalize tenant_id onto them too for simpler RLS; RECOMMENDED: denormalize.)
```

**Implementation note on RLS:** every backend DB session must call `SET LOCAL app.current_tenant_id = '<uuid>'` at the start of each request (in a FastAPI dependency, before any query executes) — sourced from the authenticated user's JWT, never from a client-supplied parameter. This is the single most important security control in the system; write an integration test that attempts a cross-tenant read and asserts it returns zero rows.

---

## 5. LangGraph Agent Design

### 5.1 State schema
```python
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
    response_attachments: Optional[list[dict]]  # [{type: "pdf", url: "..."}]
    requires_confirmation: bool
```

### 5.2 Graph structure
```python
# graph.py — pseudocode structure, implement literally
graph = StateGraph(AgentState)

graph.add_node("classify_intent", classify_intent_node)
graph.add_node("quotation_agent", quotation_agent_node)
graph.add_node("invoice_agent", invoice_agent_node)
graph.add_node("dues_agent", dues_agent_node)
graph.add_node("stock_agent", stock_agent_node)
graph.add_node("summary_agent", summary_agent_node)
graph.add_node("clarify", clarify_node)
graph.add_node("out_of_scope_response", out_of_scope_node)
graph.add_node("log_conversation", log_conversation_node)

graph.set_entry_point("classify_intent")

graph.add_conditional_edges(
    "classify_intent",
    route_by_intent,   # reads state["detected_intent"]
    {
        "quotation": "quotation_agent",
        "invoice": "invoice_agent",
        "dues": "dues_agent",
        "stock": "stock_agent",
        "summary": "summary_agent",
        "clarify": "clarify",
        "out_of_scope": "out_of_scope_response",
    }
)

# every terminal agent node routes to log_conversation, then END
for node in ["quotation_agent","invoice_agent","dues_agent","stock_agent","summary_agent","clarify","out_of_scope_response"]:
    graph.add_edge(node, "log_conversation")
graph.add_edge("log_conversation", END)
```

### 5.3 Intent classification node
Implemented as a single LLM call with **function-calling / structured output**, not free-text parsing. Define the intent schema as a tool/function the LLM must call:

```json
{
  "name": "classify_business_intent",
  "description": "Classify the owner's message into exactly one business intent and extract known entities.",
  "parameters": {
    "type": "object",
    "properties": {
      "intent": {
        "type": "string",
        "enum": ["quotation", "invoice", "dues", "stock", "summary", "clarify", "out_of_scope"]
      },
      "customer_name": {"type": "string", "nullable": true},
      "item_name": {"type": "string", "nullable": true},
      "quantity": {"type": "number", "nullable": true},
      "confidence": {"type": "number"}
    },
    "required": ["intent", "confidence"]
  }
}
```
**Routing rule:** if `confidence < 0.6` OR required entities for the classified intent are missing, route to `clarify` instead of the target agent. Never let a low-confidence classification silently execute a write action.

### 5.4 Tool contracts (each agent's callable tools — implement as typed Python functions, exposed to LangGraph as tools)

```python
# customer_tools.py
def lookup_customer(tenant_id: str, name: str) -> Optional[Customer]:
    """Fuzzy-match against customer.name using pg_trgm similarity, threshold 0.4."""

def create_customer(tenant_id: str, name: str, phone: str | None = None) -> Customer:
    """Creates a new customer row, returns it."""

# item_tools.py
def lookup_item(tenant_id: str, name: str) -> Optional[Item]:
    """Fuzzy-match against item.name."""

# quotation_tools.py
def create_quotation(tenant_id: str, customer_id: str, lines: list[QuotationLineInput]) -> Quotation:
    """Creates quotation + quotation_line rows, computes subtotal, generates quotation_number
    (format: Q-{YYYYMM}-{sequential}), triggers PDF generation, returns Quotation with pdf_url."""

# invoice_tools.py
def create_invoice_from_quotation(tenant_id: str, quotation_id: str) -> Invoice:
    """Converts quotation lines into invoice lines, runs gst_calculator per line,
    generates invoice_number (format: INV-{YYYYMM}-{sequential}), decrements stock,
    generates PDF, returns Invoice."""

def create_invoice_direct(tenant_id: str, customer_id: str, lines: list[InvoiceLineInput]) -> Invoice:
    """Same as above but without a prior quotation."""

# stock_tools.py
def get_stock_level(tenant_id: str, item_id: str) -> StockLevel:
    """Returns quantity_available + last_updated."""

def decrement_stock(tenant_id: str, item_id: str, quantity: float) -> None:
    """Called internally by create_invoice_* — never exposed directly to the LLM as a standalone tool."""

# payment_tools.py
def get_overdue_invoices(tenant_id: str) -> list[Invoice]:
    """WHERE status != 'paid' AND due_date < CURRENT_DATE, ordered by days overdue desc."""

def send_payment_reminder(tenant_id: str, invoice_id: str) -> ReminderResult:
    """Sends a WhatsApp template message (approved template required for outside-session-window sends),
    logs to conversation_log with channel='whatsapp', direction='outbound'."""
```

**Tool exposure rule:** each agent node only has access to its own tool subset (Quotation Agent cannot call `send_payment_reminder`, Stock Agent cannot call `create_invoice_direct`). Enforce this by only binding the relevant tool list per node, not by relying on prompt instructions alone.

---

## 6. GST Calculator (deterministic, unit-test this exhaustively)

```python
# gst_calculator.py
from decimal import Decimal, ROUND_HALF_UP

def calculate_line_tax(unit_price: Decimal, quantity: Decimal, gst_rate_percent: Decimal,
                        business_state: str, customer_state: str) -> dict:
    """
    Returns: {subtotal, cgst, sgst, igst, total}
    Rule: if business_state == customer_state -> split gst_rate_percent evenly into CGST+SGST.
          else -> full gst_rate_percent as IGST.
    All rounding: ROUND_HALF_UP to 2 decimal places, applied at the LINE level, then summed
    (do not round only at the invoice total level — line-level rounding is what GST compliance expects).
    """
    subtotal = (unit_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tax_amount = (subtotal * gst_rate_percent / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if business_state == customer_state:
        half = (tax_amount / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cgst, sgst, igst = half, tax_amount - half, Decimal("0.00")
    else:
        cgst, sgst, igst = Decimal("0.00"), Decimal("0.00"), tax_amount

    total = subtotal + cgst + sgst + igst
    return {"subtotal": subtotal, "cgst": cgst, "sgst": sgst, "igst": igst, "total": total}

def calculate_invoice_totals(lines: list[dict]) -> dict:
    """Sums calculate_line_tax results across all lines. Pure summation, no re-rounding of the sum."""
```

**Required unit tests (write these, do not skip):**
- Intra-state split is exactly even (or off-by-one-paisa handled deterministically, not randomly)
- Inter-state produces IGST only, CGST/SGST are zero
- Zero-quantity or zero-price line raises a validation error, does not silently produce a zero-tax line
- Rounding behavior matches expected GST-compliant rounding (line-level, not aggregate-level)

---

## 7. PDF Generation

- Templates in `app/templates/quotation.html` and `invoice.html`, Jinja2, rendered to HTML then WeasyPrint → PDF.
- Required template variables: `tenant` (name, logo_url, address, gstin), `customer` (name, address, gstin), `document_number`, `date`, `lines` (item name, qty, unit price, gst_rate, line_total), `subtotal`, `cgst`, `sgst`, `igst`, `total`, and for invoices specifically: `due_date`, a UPI payment string placeholder (`upi://pay?pa=placeholder&am={total}` — static, not a live payment gateway per PRD scope).
- Store rendered PDFs in Supabase Storage under `documents/{tenant_id}/{document_type}/{document_id}.pdf`; save the resulting URL to `quotation.pdf_url` / `invoice.pdf_url`.
- PDF generation must be synchronous in the request path for MVP (acceptable latency at this scale) — do not build a background job queue for this in MVP; if generation takes long enough to be noticeable, that's a signal to revisit post-MVP, not a reason to add infrastructure now.

---

## 8. CSV Onboarding Validation

### 8.1 Template columns

`items.csv`: `name` (required), `hsn_code` (required), `gst_rate_percent` (required, numeric), `unit_price` (required, numeric), `unit` (optional, default "pcs"), `opening_stock` (required, numeric).

`customers.csv`: `name` (required), `phone` (optional), `gstin` (optional), `state` (required), `address` (optional).

### 8.2 Validation pipeline behavior
```python
# csv_validator.py — behavior spec
def validate_items_csv(file) -> ValidationResult:
    """
    1. Parse with pandas, enforce column presence (fail fast with a clear message if columns missing).
    2. Row-level validation: required fields non-null, numeric fields actually numeric,
       gst_rate_percent in a sane range (0-28), unit_price > 0.
    3. Return ValidationResult(valid_rows: list[dict], errors: list[{row_number, field, message}]).
    4. NEVER partially commit on first pass — return the full preview (valid + errors) to the
       frontend for the user to review before calling /onboarding/items/bulk-confirm.
    """
```
The `/bulk-upload` endpoint only validates and returns a preview; the separate `/bulk-confirm` endpoint (called after the user reviews and accepts) performs the actual insert, inside a single DB transaction — either all valid rows commit, or none do, on confirm failure.

---

## 9. API Contracts (request/response shapes)

### `POST /auth/otp/request`
```json
// Request
{ "phone": "+91XXXXXXXXXX" }
// Response 200
{ "status": "sent" }
```

### `POST /auth/otp/verify`
```json
// Request
{ "phone": "+91XXXXXXXXXX", "otp": "123456" }
// Response 200
{ "session_token": "<jwt>", "tenant_id": "<uuid>|null", "onboarding_complete": false }
```

### `POST /chat/message`
```json
// Request
{ "message": "Quotation for Ramesh Traders, 200 units Steel Rod 12mm", "channel": "web" }
// Response 200
{
  "response_text": "Here's your quotation for Ramesh Traders.",
  "attachments": [{ "type": "pdf", "url": "https://.../quotation_Q-202608-0001.pdf" }],
  "requires_confirmation": false
}
```

### `POST /onboarding/items/bulk-upload`
```json
// multipart/form-data with CSV file
// Response 200
{
  "valid_rows": [ { "name": "Steel Rod 12mm", "hsn_code": "7213", "gst_rate_percent": 18, "unit_price": 450, "opening_stock": 500 } ],
  "errors": [ { "row_number": 14, "field": "gst_rate_percent", "message": "Must be numeric between 0-28" } ]
}
```

### `POST /onboarding/items/bulk-confirm`
```json
// Request: the reviewed/edited valid_rows array from the preview step
// Response 200
{ "inserted_count": 213, "tenant_id": "<uuid>" }
```

### `GET /dashboard/summary`
```json
// Response 200
{
  "date": "2026-08-07",
  "quotations_sent_today": 4,
  "invoices_generated_today": 2,
  "amount_collected_today": 15400.00,
  "amount_pending_total": 84200.00,
  "low_stock_items": [ { "item_name": "Steel Rod 12mm", "quantity_available": 8 } ]
}
```

### `POST /webhooks/whatsapp`
Standard Meta Cloud API webhook payload shape (implement per Meta's documented structure — verify signature using `X-Hub-Signature-256` header against `WHATSAPP_VERIFY_TOKEN` before processing; reject unverified requests with 403). On verified receipt: extract `from` (phone), `text.body` or `document`/`image` payload, map phone → `app_user` → `tenant_id`, then invoke the same `AgentState` graph as `/chat/message` with `channel="whatsapp"`.

---

## 10. Frontend Implementation Notes

- **Auth state:** store `session_token` in memory + httpOnly-cookie-equivalent pattern is not available for a pure SPA — use `localStorage` for MVP with a documented note that this is acceptable for MVP only, revisit for production hardening (short-lived JWT + refresh token pattern) post-MVP.
- **Chat panel component:** polls or (preferably) uses a lightweight WebSocket/SSE connection to `/chat/history` so messages sent via WhatsApp appear in the web chat panel without a manual refresh — for MVP, simple polling every 5 seconds is an acceptable fallback if WebSocket adds too much time.
- **Onboarding wizard:** implement as a controlled multi-step form with state persisted to the backend at each step (not only on final submit) — if the owner closes the tab mid-onboarding, they should resume, not restart.
- **CSV bulk upload UI:** must render the `errors` array from the validation response as an inline, row-numbered list the user can act on, and allow re-upload without losing already-valid rows from the previous pass if feasible; if not feasible in MVP timeline, at minimum show a clear "213 valid, 4 errors — fix your file and re-upload" state.

---

## 11. Error Handling & Logging Standards

- All API errors return a consistent shape: `{ "error": { "code": "string", "message": "human-readable" } }`.
- Agent-layer failures (LLM timeout, tool execution failure) must degrade to a user-facing message like "Something went wrong generating that — try rephrasing, or type 'help'" — never leak a stack trace or raw exception to WhatsApp or the web chat.
- Every tool call (Section 5.4) wraps its DB writes in a transaction; on failure, roll back and log the failure to `conversation_log` with `agent_invoked` set and a note in a separate `error_log` table (add this table if not already present) — do not fail silently.
- Structured logging (JSON logs) at minimum for: every inbound message, every intent classification result, every tool invocation, every PDF generation, every WhatsApp send attempt and its delivery status.

---

## 12. Testing Requirements (minimum bar before calling MVP "done")

| Area | Required tests |
|---|---|
| `gst_calculator.py` | Full unit test suite per Section 6 |
| `csv_validator.py` | Valid file, missing column, bad data type, empty file, oversized file |
| RLS | Integration test proving cross-tenant read returns empty, not an error and not real data |
| Agent routing | Unit tests for `classify_intent` node covering all 7 intents + one ambiguous/low-confidence case |
| End-to-end | At least one scripted test per feature: quotation creation, quotation→invoice conversion, dues lookup + reminder send (mock the actual WhatsApp send), stock lookup and post-invoice decrement |
| Onboarding | Full flow test: business profile → CSV upload → confirm → items queryable afterward |

---

## 13. Deployment (MVP/pilot stage)

- **Backend:** containerize with a single `Dockerfile`; deploy to Railway or Fly.io (small always-on instance, not serverless, since LangGraph agent state benefits from a warm process).
- **Database:** Supabase-hosted Postgres (managed backups included).
- **Frontend:** static build deployed to Vercel or Netlify, pointed at the backend API URL via env var.
- **WhatsApp webhook:** production Meta webhook URL points at the deployed backend directly (no ngrok needed once deployed — ngrok is a local-dev-only tool, remove any dependency on it from anything beyond local development docs).
- **CI:** GitHub Actions running the test suite (Section 12) on every PR; block merge on failure.

---

## 14. Security Checklist (verify before onboarding any real pilot business)

- [ ] RLS enabled and tested on every tenant-scoped table
- [ ] JWT secret is a strong, environment-specific value, never the example/default
- [ ] Meta webhook signature verification implemented and tested (reject unsigned/invalid requests)
- [ ] No customer/financial data logged in plaintext application logs beyond what Section 11 specifies
- [ ] File uploads (CSV via onboarding, files forwarded via WhatsApp) are size-limited and type-validated before parsing
- [ ] Supabase service role key is backend-only, never shipped to the frontend bundle

---

## 15. Definition of Done Per Feature (acceptance criteria)

**Quotation:** Owner can type a natural-language quotation request on either channel, unknown customer/item triggers a clarifying question, resulting PDF is correctly formatted and downloadable, quotation_number is unique and sequential per tenant.

**Invoice:** Owner can convert an existing quotation or create an invoice directly; GST split is correct for both intra-state and inter-state cases (verified against unit tests); stock decrements correctly; invoice_number is unique and sequential per tenant; PDF renders with correct tax breakdown.

**Dues:** Owner can ask "who owes me money" and get an accurate, sorted-by-overdue list; "send reminders" triggers actual WhatsApp template sends (verified in a test/pilot WhatsApp number) and logs each send.

**Stock:** Owner can ask stock level for a fuzzy-matched item name; level reflects any invoices created since onboarding; low-stock items surface on the dashboard summary.

**Onboarding:** All three catalog input paths (manual, CSV, WhatsApp-forwarded file) result in queryable, correct item/customer records; business GST profile is required and enforced before first invoice generation is allowed.

---

*This TRD is implementation-complete for the four locked MVP features. Any request to add scope beyond Section 1's repository structure and the four features in the PRD should be treated as a new project phase, not folded into this build.*
