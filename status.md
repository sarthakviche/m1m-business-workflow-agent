# Munim.ai (M1M) — Project Status & Capability Report

> **Generated Date:** November 16, 2026  
> **Environment:** Local Development (Windows)  
> **Backend Service:** FastAPI on `http://127.0.0.1:8000` (Status: Healthy / Ready)  
> **Frontend Web App:** React 19 + Vite 8 on `http://localhost:5173` (Status: Running)  
> **Test Suite:** 316 passed, 4 skipped (100% passing)

---

## 1. Repository & Git Status

### Current Branch & Commits
* **Active Branch:** `feat/saas-foundation`
* **Local vs. Remote:** **Your local branch is ahead of `origin/feat/saas-foundation` by 1 commit:**
  * `01877fe` — *"feat: add motion-led landing page and explainer film source"* (includes marketing landing page, explainer video assets, and motion sources).
  * **Action Required:** Run `git push origin feat/saas-foundation` to publish this commit to GitHub.
* **Working Tree:** Clean (all tracked files committed).

### Branch Sync Status Across Repository
* **`origin/staging`:** Has commit `caa604a` (*"Merge pull request #3 from sarthakviche/feat/saas-foundation"*). Local `feat/saas-foundation` has not yet been merged into `staging`.
* **`main`:** Behind `origin/main` by 1 commit (`346b978`).
* **`feat/added-chatfall-back-postgres`:** Ahead of its remote tracking branch by 2 commits.

---

## 2. Features Complete End-to-End (End-User POV)

From the perspective of a small-business owner or staff member, the following capabilities are fully functional and interactive today:

### A. AI Assistant ("Munim Chat")
* **Conversational Quotation Creation:**
  * Type in natural language (English / Hinglish): *"Create a quotation for Ramesh Traders: 10 bags Cement 50kg, 5 rolls Binding Wire"*.
  * Munim resolves the customer (with fuzzy name matching), searches catalog products, calculates GST deterministically, generates a sequential quote number (`Q-YYYYMM-XXX`), and produces a printable PDF.
* **Conversational Tax Invoice Creation:**
  * Type: *"Create invoice for Ganesh Engineering for 20 pcs Hex Bolt M10"*.
  * Munim checks real-time inventory, safely decrements available stock, calculates exact intra-state (CGST + SGST) or inter-state (IGST) taxes, creates invoice number (`INV-YYYYMM-XXX`), and renders a GST-compliant tax invoice PDF.
* **Quotation to Invoice Conversion:**
  * Type: *"Convert quotation Q-202611-001 to invoice"*.
  * Munim validates that the quote exists, verifies stock for every item, deducts stock atomically, transitions quotation status to `converted`, and issues the invoice.
* **Multi-Turn Clarification Memory:**
  * If the user provides incomplete information (e.g. *"Make an invoice for Ramesh"* without items, or *"10 steel rods"* without mentioning the customer), Munim asks follow-up questions and retains context across turns until the request is fulfilled.
* **Instant Document Cards:**
  * Chat returns rich preview cards with the total amount, status pill, and a direct 1-click PDF download button.
* **Catalog Querying via Chat:**
  * Type: *"What is the price of Steel Rod?"* — Munim queries the catalog and reports price, GST rate, HSN, and in-stock quantity.

### B. Product Catalog & Live Inventory
* **Catalog Directory:** Browse items with HSN codes, GST slabs (0%, 5%, 12%, 18%, 28%, 40%), unit prices, units of measure (`pcs`, `kg`, `mtr`, `box`, `ltr`, etc.), and available stock.
* **Real-time Stock Tracking:** Stock is linked 1:1 with catalog items and decrements automatically on invoice generation.
* **Low Stock Alerts:** Items at or below 10 units are automatically flagged across the application.

### C. Photo / PDF / CSV Catalog & Price-List Import (Already Built!)
* **Smart Upload (`/inventory/import`):**
  * Business owners can take a photo of a printed or handwritten rate card, price list, PDF, or CSV and upload it.
  * **Gemini Multimodal AI** reads and transcribes every item name, unit price, unit, HSN, and stock quantity.
  * **Interactive Review Table:** Before anything is written to the database, the user reviews every extracted row in an editable grid. The UI flags issues (e.g., missing GST rates or prices) and highlights whether the item is new, an update to an existing product, or unchanged.
  * **Atomic Save:** 1-click batch import creates or updates both the catalog item and stock records in a single database transaction.

### D. Business Health Dashboard (`/dashboard`)
* **Real-Time Financial Metrics:**
  * Total Sales (₹)
  * Amount Received vs. Outstanding Dues (₹)
  * Unpaid Invoice Count & Total Open Quotations Value
  * Active Customer Count & Catalog Item Count
* **Actionable Feeds:**
  * Low Stock warning list.
  * Recent Documents timeline with status tags and 1-click PDF download.

### E. Customer Directory (`/customers`)
* Directory of all customers with phone numbers, GSTIN, registered billing state, and address.
* Aggregated metrics per customer: total quotation count, total invoice count, and cumulative billed revenue.

### F. Document Vault & In-App PDF Viewer (`/documents`)
* Unified searchable and filterable list of all issued Quotations and Invoices.
* Filter by document type (`quotation` vs `invoice`), search by customer name or document number.
* 1-click PDF view and direct download.

### G. Professional GST-Compliant Document Engine
* Automated PDF generation using Jinja2 templates styled specifically for Indian B2B/B2C trade.
* Includes:
  * Company logo/monogram, business GSTIN, PAN, and full address.
  * Buyer details with customer GSTIN and state.
  * Item table with HSN code, quantity, unit, unit rate, taxable value, and tax breakdown.
  * Split tax calculation: automatically selects CGST + SGST for intra-state sales or IGST for inter-state sales based on buyer/seller states.
  * Grand total formatted in Indian numbering system and printed in words (Lakhs / Crores).
  * Bank details, payment terms, and authorized signatory placeholder.

### H. Multi-Channel Messaging (Telegram Integration)
* Built-in Telegram bot channel.
* Linking flow: Business owners generate a secure 6-character link code in Settings and send it to the Telegram bot to pair their mobile account.
* Execute quotes and invoices directly from a mobile messaging app without opening a laptop.

---

## 3. Database Architecture: What & How Data is Stored

### Storage Engines
* **Local Development:** SQLite via `aiosqlite` (`m1m.db` at workspace root). Zero external configuration required.
* **Staging / Production:** PostgreSQL via `asyncpg` (Supabase-ready) with connection pooling and SSL.
* **Migration Engine:** Alembic manages schema versions (Current: `b4f1c7e82d10 (head)`).

### Multi-Tenant Model
Every tenant-scoped table enforces strict isolation via a `tenant_id` foreign key referencing `tenant.id` with `ondelete="CASCADE"`. Cross-tenant data leaks are prevented at the query and dependency level.

### Detailed Table Breakdown (15 Tables)

| Table | What It Stores | How It Stores It |
|---|---|---|
| `tenant` | Business identity and tax configuration | UUID PK, `business_name`, `gstin`, `state` (used for GST intra/inter-state logic), `address`, `logo_url`, `onboarded_at`, timestamps. |
| `app_user` | Login credentials mapping and user roles | UUID PK, `tenant_id` (FK), `auth_subject` (Supabase Auth UID), `email`, `phone`, `name`, `role` (`owner`, `staff`, `accountant`). |
| `customer` | Buyer directory | UUID PK, `tenant_id` (FK), `name`, `phone`, `gstin`, `state` (determines tax jurisdiction), `address`. Indexed for fuzzy matching. |
| `item` | Product catalog | UUID PK, `tenant_id` (FK), `name`, `hsn_code`, `gst_rate_percent` (Numeric), `unit_price` (Numeric), `unit` (e.g. `pcs`, `kg`). |
| `stock` | Live inventory balance | `item_id` is both PK and FK (enforces strict 1:1 with `item`), `tenant_id` (FK), `quantity_available` (Numeric(12,2) for fractional units like kg), `last_updated`. |
| `quotation` | Sales estimates/proposals | UUID PK, `tenant_id` (FK), `customer_id` (FK), unique `quotation_number` (`Q-YYYYMM-XXX`), `status` (`draft`, `sent`, `converted`), `subtotal`, `pdf_url`. |
| `quotation_line` | Line items in a quotation | UUID PK, `quotation_id` (FK), `item_id` (FK), `quantity`, `unit_price`, `line_total`. |
| `invoice` | Legally binding GST tax invoices | UUID PK, `tenant_id` (FK), `customer_id` (FK), optional `quotation_id` (FK), unique `invoice_number` (`INV-YYYYMM-XXX`), `subtotal`, `cgst_amount`, `sgst_amount`, `igst_amount`, `total_amount`, `status` (`unpaid`, `partially_paid`, `paid`), `due_date`, `pdf_url`, `tally_push_status`. |
| `invoice_line` | Line items in a tax invoice | UUID PK, `invoice_id` (FK), `item_id` (FK), `quantity`, `unit_price`, **denormalized `gst_rate_percent`** (preserves historical tax rate if catalog changes), `line_total`. |
| `payment` | Payment records received against invoices | UUID PK, `invoice_id` (FK), `amount`, `method` (`upi`, `cash`, `bank_transfer`), `paid_at`. Updates invoice status automatically. |
| `document_file` | **Tamper-proof PDF binary storage** | Composite PK (`tenant_id`, `doc_type`, `filename`), `content` (**LargeBinary / bytea blob**), `created_at`. PDFs live directly in the database so free/serverless restarts never lose files! |
| `document_sequence` | Gapless sequential numbering counters | Composite PK (`tenant_id`, `prefix`), `last_number` (Integer). Atomic counter prevents gaps or collisions in invoice/quote numbers. |
| `conversation_log` | Omnichannel interaction audit trail | UUID PK, `tenant_id` (FK), `conversation_id`, `channel` (`web`, `telegram`, `whatsapp`), `direction` (`inbound`, `outbound`), `raw_message`, `detected_intent`, `agent_invoked`, `created_at`. |
| `conversation_state` | Multi-turn in-progress conversation cache | `conversation_id` PK, `tenant_id` (FK), `state` (**JSON**), `updated_at`. Automatically cleaned up when intent completes. |
| `ai_usage` | Daily AI quota counter | Composite PK (`tenant_id`, `usage_date`), `calls` (Integer). Protects against unexpected Gemini API usage spikes. |
| `channel_identity` / `channel_link_code` / `channel_inbound_event` | Messaging channel linkage & webhook deduplication | Stores Telegram user IDs mapped to tenants, single-use SHA-256 link codes with expiration, and unique external event IDs to guarantee idempotency. |
| `tally_connection` / `external_id_map` | ERP integration staging | Per-tenant sync status and mapping between internal UUIDs and external Tally GUIDs. |

---

## 4. Evaluation of Next Features (Current Status & Roadmap)

| Feature | Current Status | Details & Implementation Plan |
|---|---|---|
| **Multi-user Login** | **Partially Implemented (Foundation Ready)** | • **Done:** Schema support (`app_user` table supports `owner`, `staff`, `accountant` roles linked to one business; Supabase auth integration).<br>• **To Add:** Team invitation UI in Settings (invite via email/phone), role-based permission enforcement in API (e.g. staff can issue quotes, accountant can view ledger, owner can modify GSTIN/delete data). |
| **Talk to my Business (Ask Munim about inventory, sales, dues)** | **Partially Implemented** | • **Done:** Product stock & price inquiry (`search_products` tool).<br>• **To Add:** Conversational Business Intelligence agent: allow queries like *"How much sales did we do this week?"*, *"Who owes the most money?"*, *"Which items are low in stock?"*, *"Who are my top 3 buyers this month?"*. |
| **AI Tips about Business (Data-Driven Insights)** | **To Add** | • **To Add:** Proactive AI business analyzer node. Evaluates sales patterns and alerts the user on:<br>  1. Overdue customer invoices with follow-up nudges.<br>  2. Dead or slow-moving stock recommendations.<br>  3. Top-selling seasonal items that need restocking.<br>  4. High margin vs. low margin item insights. |
| **Pretty Invoices and Quotations** | **Complete (With Polish to Add)** | • **Done:** Fully styled, responsive GST invoice and quotation PDF templates with clean typography, Indian number formatting (words and currency), and tax breakdown.<br>• **To Add:** Custom color scheme / brand accents, business logo upload directly from Settings UI, and **dynamic UPI QR codes** embedded on invoices for instant customer payment. |
| **Customer Import via Phone Contact Card (.vcf)** | **To Add** | • **To Add:** Support importing `.vcf` / vCard files or sharing phone contacts directly in Chat or Customers tab. Parse customer name, phone number, address, and notes into the `customer` database without manual typing. |
| **Automatic Product Entry, Stock & Price via Photo (Onboarding & Ongoing)** | **COMPLETE END-TO-END** | • **Done:** Fully implemented in backend (`catalog_import.py`) and frontend (`ImportCatalog.tsx` & `BulkUpload.tsx`).<br>• End-to-end workflow: Upload phone camera photo / PDF / CSV -> Gemini text & structure extraction -> interactive review table -> atomic database upsert.<br>• Available **both during onboarding** and **anytime later** via `/inventory/import`. |

---

## 5. How to Run the Project Locally

### 1. Backend (FastAPI)
```powershell
cd d:\development\m1m-business-workflow-agent\backend
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* Health Check: `http://127.0.0.1:8000/health`
* Interactive API Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend (React + Vite)
```powershell
cd d:\development\m1m-business-workflow-agent\frontend
npm run dev
```
* App URL: `http://localhost:5173` (proxies `/api` and `/documents` to port 8000)

### 3. Run Test Suite
```powershell
cd d:\development\m1m-business-workflow-agent\backend
.\.venv\Scripts\python.exe -m pytest
```
