# M1M Feature Inventory and Delivery Roadmap

**Repository review date:** 28 September 2026  
**Current checkout:** `feat/added-chatfall-back-postgres` at `c14a58a`  
**Newest remote commit inspected:** `origin/vedika-whatsapp-pdf-staging` at `9f2b03c` (10 September 2026)

## Repository status and update decision

Remote references were fetched successfully. The current branch is one local commit ahead of its tracked remote, and the working tree contains an existing modification to `m1m.db`; that file has not been touched.

`9f2b03c` is the chronologically newest remote code. It is **not** a fast-forward successor of the current branch: both lines diverge from `00c8b03`. Its UI changes also delete/rework parts of the current hardened agent implementation and documentation. Therefore, it must be reviewed and deliberately merged or cherry-picked; it has not been automatically pulled into this branch.

## What works in the current checkout

| Area | Current implementation | Evidence / limits |
| --- | --- | --- |
| Conversational business agent | FastAPI `POST /api/v1/chat` invokes a LangGraph workflow with conversation history. | Web is the active channel; the tenant is selected from configuration, not user identity. |
| Intent handling | Quotation, invoice, catalog query, clarification, future-feature and off-topic routing. Gemini extraction falls back to regex parsing. | The offline regex parser is limited for complex multi-item requests. |
| Quotation generation | Natural-language quotation creation, fuzzy customer resolution/creation, sequential document number, persisted lines, and PDF URL. | Customer confirmation is required for medium-confidence matches. |
| GST invoices | Direct invoices and quotation-to-invoice conversion, deterministic `Decimal` GST calculations, CGST/SGST versus IGST, and PDF generation. | E-invoicing/IRN and e-way bills are not implemented. |
| Inventory safety | Invoice creation verifies stock and decrements inventory in the transaction; catalog queries expose item price, HSN, GST rate, and stock. | There is no full inventory-management UI or advanced warehouse features. |
| Customer resolution | Exact/normalized/fuzzy lookup with high, medium-confirmation, and new-customer bands. | No government GSTIN lookup. |
| Document access | Generated PDF files are served safely; `GET /api/v1/documents` lists current-tenant quotation/invoice history. | The current React app is chat-focused, so this API is not yet surfaced as a complete management screen. |
| Data and resilience | SQLAlchemy async models, Alembic schema, SQLite/Postgres configuration, tenant-scoped queries, conversation audit log, PDF fallback. | No production authentication or database row-level security policy enforcement. |

## Newer remote branch: UI work awaiting integration

The newest remote branch (`origin/vedika-whatsapp-pdf-staging`) adds React pages for a dashboard, chat, customers, documents, and inventory, plus WhatsApp-themed chat/PDF presentation. This is valuable progress, but it is **not yet integrated into this checkout** and should not be described as a confirmed end-to-end feature until its API contracts are reconciled.

Important integration gaps found during review:

- The added pages use a hard-coded phone number and endpoints such as `/invoices/`, `/quotations/`, `/items/`, and `/customers/`.
- The current backend exposes `/api/v1/chat`, `/api/v1/documents`, and document file-serving routes; it does not expose that complete management API surface.
- The newer branch modifies agent/configuration code and removes current technical documentation/assets. Merge work must retain the GST, stock, tenant, and fallback protections that are already present here.

## Product scope: what we are building

The approved MVP PRD defines exactly four customer-facing capabilities across one shared business workflow engine:

1. **Quotation generation** — create a branded quotation from natural language and deliver a PDF.
2. **GST invoice generation** — create a compliant tax invoice directly or from a quotation, then decrement stock safely.
3. **Pending payments and dues** — show unpaid/overdue invoices and send logged WhatsApp payment reminders.
4. **Inventory and stock checks** — return current stock on request and maintain quantities on invoicing.

Two surfaces use the same records and conversation history:

- **Web app:** phone/OTP login, onboarding, dashboard, chat, documents, customers, inventory, and settings.
- **WhatsApp:** Meta Cloud API inbound/outbound messages, including quotation/invoice PDF delivery and approved reminder templates.

The following are explicitly outside MVP: live Tally/Zoho/Busy sync, live payment collection, payroll, delivery booking, multi-language/voice/OCR, multi-warehouse, and CRM/lead management. Tally remains a clearly labeled read-only simulation in this phase.

## Delivery backlog

### P0 — Integrate and stabilize the chosen code line

- Decide whether `origin/vedika-whatsapp-pdf-staging` is the intended source for the new web UI.
- Merge/cherry-pick its UI pages while preserving the current hardened agent, tests, fallback chains, and documentation.
- Replace hard-coded phone/host values with shared typed API configuration.
- Verify every page against the actual FastAPI contracts before calling it complete.

### P1 — Complete the web foundation

- Add phone/OTP authentication and derive the tenant/user from the authenticated session.
- Build onboarding: business/GST profile, manual catalog/customer entry, CSV/Excel validation-preview-confirm workflow, and initial stock.
- Implement tenant-scoped CRUD APIs and responsive UI for customers and inventory.
- Connect dashboard metrics and documents list/download actions to real APIs.

### P2 — Finish the four MVP workflows

- **Quotation/invoice:** test web UI to agent/API flow, document history, conversion guardrails, and PDF download.
- **Stock:** expose stock levels and stock movement history; add low-stock alerts to dashboard/chat.
- **Dues:** calculate outstanding and overdue balances, record payments, list dues by customer, and make reminder sending auditable.

### P3 — WhatsApp channel

- Implement and verify Meta webhook signature handling, phone-to-tenant/user mapping, and shared conversation history.
- Send quotation/invoice PDFs over WhatsApp.
- Add approved payment-reminder templates and message delivery logging.

### P4 — Production readiness

- Move production deployment to Postgres with tenant isolation enforced by RLS, secrets management, and migrations.
- Add role-based access, object storage for documents, observability, rate limits, and end-to-end multi-tenant tests.
- Add high-scale document-numbering coordination only when multi-instance deployment requires it.

## Definition of complete for the MVP

The MVP is complete when an authenticated business can onboard its GST profile, catalog, stock, and customers; create a quotation and convert it into a GST invoice from either web chat or WhatsApp; receive the PDF; see the same history on both channels; check stock; view and remind overdue customers; and have every result isolated to that business and recorded in the audit trail.

## Recommended first implementation slice

Start by integrating the newer dashboard/chat/documents/customers/inventory UI with the current backend through a single typed API layer, then implement the missing tenant-scoped management endpoints. This creates a usable, testable web shell without weakening the existing document-generation and tax/stock safeguards, and it provides the foundation required for dues and WhatsApp work.
