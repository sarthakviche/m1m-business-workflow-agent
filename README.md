# M1M — Munim.ai

> **Business copilot for Indian SMEs** — Quotation, Invoice, Dues tracking, and Inventory via WhatsApp + Web.

---

## Project Overview

M1M (Munim.ai) is an AI-powered business assistant that lets Indian SME owners manage their business operations through natural language — either on WhatsApp or a web app. A single agent brain handles quotation generation, GST-compliant invoice generation, dues tracking, and stock checking.

This repository is built incrementally in sprints. **Sprint 1** focuses on proving the core pipeline end-to-end: natural language → backend → agent → correct calculations → PDF.

---

## Sprint 1 Scope

### In scope
1. Database schema + seed data (Step 1 — **current**)
2. Gemini API smoke test
3. Deterministic GST calculator
4. Quotation Agent
5. Invoice Agent
6. Minimal developer test UI (chat-style)
7. PDF generation
8. WhatsApp Cloud API integration (after internal test UI validates backend)

### Out of scope in Sprint 1
- Onboarding wizard / business signup
- CSV upload
- Authentication (OTP, JWT sessions)
- Dues Agent / Stock Query Agent
- Full dashboard / customer / inventory dashboards
- Production customer-facing web app
- Multi-tenant isolation testing
- Tally integration
- Payment gateway, OCR, voice notes, analytics, deployment

> ⚠️ **Sprint 2+ blocker:** RLS (Row-Level Security) and cross-tenant isolation testing are **intentionally deferred to Sprint 2+**. Before onboarding a second real business, proper multi-tenant isolation and RLS policies must be implemented and tested.

---

## Implementation Status

| Step | Description | Status |
|------|-------------|--------|
| **Step 1** | Database schema + Alembic migration + seed script + verification | ✅ Complete |
| Step 2 | Gemini API smoke test | ⏳ Not started |
| Step 3 | Deterministic GST calculator | ⏳ Not started |
| Step 4 | Quotation Agent (LangGraph) | ⏳ Not started |
| Step 5 | Invoice Agent (LangGraph) | ⏳ Not started |
| Step 6 | Developer test UI | ⏳ Not started |
| Step 7 | PDF generation | ⏳ Not started |
| Step 8 | WhatsApp Cloud API | ⏳ Not started |

---

## Local Setup

### Prerequisites
- Python 3.11+
- A Supabase project with PostgreSQL (or any PostgreSQL 15+ instance)
- pip

### 1. Clone and set up environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and fill in your DATABASE_URL
# Format: postgresql://user:password@host:5432/dbname
```

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Run Alembic migration

```bash
# From the workspace root (m1m/)
alembic -c backend/alembic.ini upgrade head
```

This creates all 13 database tables as defined in `m1m-mvp-trd.md`.

### 4. Seed the database

```bash
# From the workspace root (m1m/)
python backend/scripts/seed.py
```

Seeds 1 test tenant, 8 customers, 12 items, and 12 stock records.

### 5. Run seed again (verify idempotency)

```bash
python backend/scripts/seed.py
```

The second run must report all records as "Existing" — no duplicates.

### 6. Run tests

```bash
# From backend/ directory
cd backend
pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string. Accepts `postgresql://` or `postgresql+asyncpg://` — the backend normalises it automatically. |
| `ENV` | No | `development` (default) or `production`. Controls SQL echo and API docs. |
| `SPRINT_TENANT_ID` | No | UUID for the Sprint 1 test tenant. If empty, falls back to the documented dev UUID `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`. |

---

## Database Schema

13 tables created by the Alembic migration:

| Table | Description |
|-------|-------------|
| `tenant` | Root of the multi-tenant hierarchy |
| `app_user` | Business staff (auth deferred to Sprint 2+) |
| `customer` | Customer records with state (for GST routing) |
| `item` | Product catalog with HSN code and GST rate |
| `stock` | 1:1 stock level per item |
| `quotation` | Quotation header |
| `quotation_line` | Line items on a quotation |
| `invoice` | GST invoice with CGST/SGST/IGST fields |
| `invoice_line` | Line items on an invoice |
| `payment` | Payment transactions against invoices |
| `conversation_log` | Append-only audit log of all agent interactions |
| `tally_connection` | Tally integration status (simulated in MVP) |
| `external_id_map` | Maps M1M entity IDs to external system IDs |

---

## Seed Data (Sprint 1 test data)

> ⚠️ **All seed data is fictional. Do not use in production.**

**Tenant:** Vaidya Industrial Supplies, Pune, Maharashtra

**Customers (8):**
- 4 Maharashtra (intra-state → CGST + SGST)
- 4 inter-state (Gujarat, Karnataka, Telangana, Delhi → IGST)

**Items (12):** Industrial/hardware catalog with GST rates:
- 5% — Safety helmet
- 12% — Bearing, cutting disc
- 18% — Steel, fasteners, electrical, welding (8 items)
- 28% — Chain pulley block

---

## Migration Commands

```bash
# Apply all pending migrations
alembic -c backend/alembic.ini upgrade head

# Show current migration status
alembic -c backend/alembic.ini current

# Show migration history
alembic -c backend/alembic.ini history

# Downgrade by one step (for rollback)
alembic -c backend/alembic.ini downgrade -1
```

---

## Verification Commands

After seeding, verify DB state directly in Supabase SQL editor:

```sql
-- Core counts
SELECT 'tenant'   AS tbl, COUNT(*) FROM tenant;
SELECT 'customer' AS tbl, COUNT(*) FROM customer;
SELECT 'item'     AS tbl, COUNT(*) FROM item;
SELECT 'stock'    AS tbl, COUNT(*) FROM stock;

-- Every item has exactly one stock row
SELECT i.name, s.quantity_available
FROM item i
JOIN stock s ON s.item_id = i.id
ORDER BY i.name;

-- Customer state distribution
SELECT state, COUNT(*) AS customer_count
FROM customer
GROUP BY state
ORDER BY customer_count DESC;

-- Item GST rate distribution
SELECT gst_rate_percent, COUNT(*) AS item_count
FROM item
GROUP BY gst_rate_percent
ORDER BY gst_rate_percent;
```

---

## Sprint 1 Limitations

1. **No authentication** — Sprint 1 uses a single hardcoded `SPRINT_TENANT_ID`. Authentication (phone + OTP, JWT) is Sprint 2+.
2. **No RLS** — Row-Level Security policies are schema-ready but not enabled. See warning below.
3. **No agents** — LangGraph agents, Gemini, GST calculator, and PDF generation are Sprint 1 Steps 2–8.
4. **No frontend** — The web app is Sprint 1 Step 6 (developer test UI), then full frontend in later sprints.
5. **Single tenant** — Only one test tenant exists. Multi-tenant behaviour is not tested in Sprint 1.

> ⚠️ **RLS and cross-tenant isolation testing are intentionally deferred to Sprint 2+.**
> Before onboarding a second business, proper multi-tenant isolation and RLS must be implemented and tested.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI 0.115+ |
| ORM | SQLAlchemy 2.x (async) |
| Driver | asyncpg |
| Migrations | Alembic 1.13+ |
| Settings | pydantic-settings 2.x |
| Database | Supabase PostgreSQL 15+ |
| Testing | pytest + pytest-asyncio |

---

*Companion documents: [`m1m-mvp-prd.md`](m1m-mvp-prd.md) · [`m1m-mvp-trd.md`](m1m-mvp-trd.md)*
