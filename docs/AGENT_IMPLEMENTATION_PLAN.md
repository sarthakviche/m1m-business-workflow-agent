# Munim — Implementation Plan for Coding Agents

> **Who this is for:** an AI coding agent (Codex, GPT-OSS, Gemini, etc.) given **one task** from section 5.
> Read sections 1–4 in full before you touch any file. They are rules, not suggestions.
> Source of truth for what already exists: [`status.md`](../status.md). Written 16 Nov 2026.

---

## 0. How to hand a task to an agent (for the human)

Paste this, replacing `T#`:

```text
You are working in the Munim repository. Read docs/AGENT_IMPLEMENTATION_PLAN.md
sections 1–4 completely, then implement ONLY task T# from section 5.
Follow every guardrail. Stay inside the files the task lists. When done, run the
checks in section 4 and reply with: files changed, test output, and anything
you could not finish. Do not commit to main or staging. Do not push.
```

One task per agent session. Review the diff yourself before merging. Run tasks in the order of section 5 unless marked independent.

---

## 1. What Munim is (30-second context)

A GST-compliant business assistant for Indian SMEs. Owners type (web chat or Telegram) *"invoice for Ramesh Traders, 10 steel rods"* and Munim creates the quotation/invoice, the PDF, and updates stock.

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy, Alembic, PostgreSQL (Supabase), LangGraph, Gemini (`google-genai`).
- **Frontend:** React 19 + Vite + TypeScript + Tailwind.
- **Multi-tenant:** every business is a `tenant`; every row carries `tenant_id`.
- **AI does language only.** It extracts intent and entities. **Prices, GST, totals, stock and document numbers are always computed by deterministic Python code.** This is the core design rule.

---

## 2. Repository map — where things go

```
backend/
  app/
    main.py                  App setup, /health, /ready, /health/agent. Touch only if the task says so.
    config.py                Settings from env. New settings go here with a safe default.
    api/v1/                  ★ ALL HTTP endpoints go here (account, catalog, chat, documents, management).
      router.py              Register new routers here.
    api/*.py                 LEGACY. Do not edit or add files here.
    agent/graph.py           LangGraph chat flow: classify → route → agent node → log.
    orchestrator/            Entry point for every chat message; RequestContext (tenant, role, permissions).
    auth/                    Login/tenant resolution. ★ DO NOT MODIFY.
    tools/
      base.py, registry.py   Tool contract. Every chat action is a registered tool.
      read/                  Read-only tools (risk_level 0).
      write/                 Tools that change data.
      __init__.py            Register new tools here.
    services/                ★ Business logic. Pure, testable, tenant-scoped functions.
      gst_calculator.py      ★ The ONLY place GST is calculated.
      doc_number.py          ★ The ONLY place document numbers are issued.
      gemini.py              ★ The ONLY place the Gemini client/model/timeouts are configured.
      intent_classifier.py   Prompt + rule-based fallback.
      pdf_service.py         Renders PDFs from Jinja2 templates.
    context_builder/         Resolves customers/items for tools.
    models/                  SQLAlchemy models, one file per table.
    db/migrations/versions/  Alembic migrations.
    errors/categories.py     All error types. Reuse them; user_message is shown to users.
    channels/telegram/       Telegram bot.
    templates/               PDF HTML templates (invoice.html, quotation.html).
  tests/                     pytest. One test file per feature.
  scripts/demo_preflight.py  Pre-demo health check.
frontend/src/
  api/client.ts              ★ The ONLY place the frontend calls the backend.
  pages/                     One file per screen.
  components/                Shared UI; components/ui.tsx has Button etc. Reuse it.
  hooks/, context/, lib/, types/
docs/                        Plans and deployment docs.
landing/, video/             Marketing site and explainer. Out of scope.
```

---

## 3. Guardrails

### 3.1 You MUST

1. **Take `tenant_id` only from `RequestContext.business_id`** (backend) — never from the request body, URL, or LLM output. Every query on a tenant table filters by `tenant_id`.
2. **Use `Decimal` for money and quantities.** Never `float` for anything stored or summed.
3. **Calculate GST only through `services/gst_calculator.py`**, and issue numbers only through `services/doc_number.py`.
4. **Put new chat abilities in a Tool** (`tools/read` or `tools/write`), with `input_schema`, `required_permissions`, `risk_level`, and register it in `tools/__init__.py`. Logic goes in a `services/` function the tool calls.
5. **Add a test for everything you add**, in `backend/tests/test_<feature>.py`. Include at least one test proving tenant B cannot see tenant A's data (copy the pattern in `tests/test_multi_tenant.py`).
6. **Write schema changes as a new Alembic migration** in `db/migrations/versions/`, with a working `downgrade()`. New columns are nullable or have a server default, so existing rows keep working.
7. **Raise errors from `errors/categories.py`** with a friendly `user_message`. Never show stack traces or raw exceptions to users.
8. **Make frontend calls through `frontend/src/api/client.ts`** and add TypeScript types there.
9. **Match the existing style:** module docstring at top, type hints, small functions, comments only where the *why* isn't obvious.
10. **Stay within the files your task lists.** If you truly need another file, say so in your final reply and explain why.
11. **Work on a branch** named `agent/T#-short-name`, cut from `feat/saas-foundation`.

### 3.2 You MUST NOT

1. **Do not modify** `app/auth/`, `app/db/session.py`, `app/rate_limit.py`, `app/idempotency/`, existing migration files, `.github/workflows/`, `Dockerfile`, or `.env*` files.
2. **Do not let the LLM produce numbers that are saved or shown as fact** (prices, totals, tax, stock, counts). The LLM may only pick a tool and its arguments.
3. **Do not add dependencies** (pip or npm) unless the task explicitly allows one. Name it in your reply.
4. **Do not change the Gemini model, timeouts, or retry settings** in `services/gemini.py`.
5. **Do not delete or rewrite existing tests** to make them pass. If one fails, fix your code. If you believe the test is wrong, stop and report it.
6. **Do not commit secrets**, API keys, real customer data, or `.env` files.
7. **Do not push, merge, or commit** to `main` or `staging`. Do not force-push.
8. **Do not make "improvements" outside your task** (renames, reformatting, refactors, dependency upgrades).
9. **Do not drop columns or tables**, or run destructive SQL.
10. **Do not edit `api/*.py` (legacy), `landing/`, or `video/`.**
11. **Do not log** message contents, tokens, phone numbers, or GSTINs at INFO level or above.

### 3.3 Stop and ask the human when

- the task seems to need changes to auth, payments, or a forbidden file;
- an existing test fails before you have changed anything;
- the task is ambiguous about business rules (tax, stock, who may do what).

Do not guess on these.

---

## 4. Definition of done (run all; paste the output)

```bash
# backend (from backend/)
../.venv/Scripts/python.exe -m pytest -q          # Windows; on Linux/macOS: pytest -q
# frontend (from frontend/)
npm run lint
npm run build
```

- All tests pass (current baseline: **324 passed, 4 skipped**). No test is skipped or deleted by you.
- `npm run build` succeeds with no TypeScript errors.
- Your final reply lists: files changed, new tests, migration id (if any), manual check steps, and open questions.

---

## 5. Tasks

Difficulty: **S** = small, any model · **M** = medium, a strong model · **L** = large, the strongest model you have, and review carefully.

### T1 — Fix nested bold in the "state missing" note · S · independent
- **Problem:** after an invoice for a customer without a state, the chat shows `**Patel Corporation**` with literal asterisks inside an italic note.
- **Files:** `backend/app/agent/graph.py` (find the "state on file" text), test in `backend/tests/test_chat_reliability.py`.
- **Done when:** the note renders the name in bold without stray `**`, and a test checks the exact string.

### T2 — Role-based permissions · M · do before T3
- **Goal:** `owner` can do everything; `staff` can create quotations/invoices and read the catalog/customers but cannot change business settings, import catalog, or manage users; `accountant` can read everything and record payments, but cannot create documents or change the catalog.
- **Files:** `backend/app/orchestrator/context.py` (map role → permission set in one function, `permissions_for_role(role)`), `backend/app/auth/dependencies.py` **read only** — pass `role` into `RequestContext` the way it is already done, `backend/app/api/v1/*.py` (call `context.require_permission(...)` on write endpoints), new test `backend/tests/test_permissions.py`.
- **Rules:** unknown roles get read-only permissions. Do not change how users log in.
- **Done when:** tests prove each role is allowed/blocked for: create invoice via chat, `PATCH /api/v1/business`, catalog import, list customers.

### T3 — Team invites · L · after T2
- **Goal:** owner invites a teammate by email with a role. The teammate signs up and is attached to the same business.
- **Files:** new model `backend/app/models/team_invite.py` (id, tenant_id, email, role, token_hash, expires_at, accepted_at), migration, endpoints in new `backend/app/api/v1/team.py` (`POST /team/invites`, `GET /team/members`, `POST /team/invites/accept`, `DELETE /team/members/{id}`), `frontend/src/pages/Settings.tsx` (Team section), `frontend/src/api/client.ts`, tests `backend/tests/test_team.py`.
- **Rules:** store only a SHA-256 hash of the invite token (copy the approach in `channels/linking.py`). Invites expire after 7 days and work once. Only owners invite or remove. An owner cannot remove themselves. **Do not send email** — return the invite link for the owner to copy. Accepting must be done by a logged-in user whose email matches.
- **Done when:** tests cover expiry, single use, wrong email, staff trying to invite, and cross-tenant access.

### T4 — "Talk to my business" read tools · M · independent
- **Goal:** chat answers *"sales this week?"*, *"who owes me the most?"*, *"what's low in stock?"*, *"top 3 customers this month?"*.
- **Files:** new `backend/app/services/business_insights.py` (pure SQL aggregation functions, tenant-scoped, returning `Decimal`s), new read tools in `backend/app/tools/read/` (`sales_summary.py`, `outstanding_dues.py`, `low_stock.py`, `top_customers.py`), register them in `tools/__init__.py`, add a `business_query` intent plus routing in `services/intent_classifier.py` (prompt **and** rule fallback) and `agent/graph.py`, tests `backend/tests/test_business_insights.py`.
- **Rules:** the LLM picks the question type and a period (`today`, `this_week`, `this_month`, `last_month`) only. All numbers come from SQL. Formatting uses `services/number_format.py` (Indian ₹ format). Periods use Asia/Kolkata time.
- **Done when:** service functions are tested with seeded data, including an empty business and tenant isolation, and the chat returns correct figures for each question.

### T5 — Business tips card · M · after T4
- **Goal:** the dashboard shows up to 3 tips: overdue invoices (unpaid and past `due_date`), slow-moving stock (no sale in 60 days but stock > 0), items selling fast and low on stock.
- **Files:** `backend/app/services/business_insights.py` (add `generate_tips`), `GET /api/v1/dashboard/tips` in `backend/app/api/v1/management.py`, `frontend/src/pages/Dashboard.tsx`, `client.ts`, tests.
- **Rules:** tips are **rule-based, not LLM**. Each tip has `kind`, `title`, `detail`, and an optional `action_prompt` (chat text the user can click to send). Hide the card when there are no tips.
- **Done when:** each rule has a test, and the card renders and links to chat.

### T6 — UPI QR code on invoices · M · independent
- **Goal:** if the business has a UPI ID, the invoice PDF shows a scannable QR for the exact amount.
- **Files:** migration adding nullable `tenant.upi_id`, `backend/app/models/tenant.py`, business settings endpoint in `api/v1/account.py` (validate the format `name@bank`), `frontend/src/pages/Settings.tsx`, `services/pdf_service.py`, `backend/app/templates/invoice.html`, tests.
- **Rules:** the QR encodes `upi://pay?pa=<upi_id>&pn=<business name>&am=<total, 2 decimals>&cu=INR&tn=<invoice number>`, URL-encoded. **Allowed new dependency:** `segno` (pure-Python QR) — embed the QR as an inline SVG/PNG data URI. No QR when `upi_id` is empty. Do not add it to quotations.
- **Done when:** a test decodes or inspects the payload string, and the PDF renders with and without a UPI ID.

### T7 — Business logo upload · M · independent
- **Files:** `POST /api/v1/business/logo` in `api/v1/account.py`; store bytes the way PDFs are stored in `document_file` (DB, not disk — the host's disk is temporary); serve through an authenticated route; use it in the PDF templates; Settings UI; tests.
- **Rules:** PNG/JPEG only, at most 1 MB, check the file signature (not just the extension). Do not resize (Pillow is not installed; do not add it). Scale the logo with CSS in the template.
- **Done when:** upload, replace, PDF with and without a logo, and wrong type/size rejection are all tested.

### T8 — Import customers from a contact card (.vcf) · S/M · independent
- **Goal:** on the Customers page, upload a `.vcf` (one or many contacts) → preview → save, the same way the catalog import works.
- **Files:** new `backend/app/services/vcard_import.py` (parse FN, TEL, ADR, NOTE yourself; **no new dependency**), `POST /api/v1/customers/import/preview` and `POST /api/v1/customers/import` in `api/v1/management.py`, `frontend/src/pages/Customers.tsx`, `client.ts`, tests with fixture files in `backend/tests/fixtures/`.
- **Rules:** never overwrite an existing customer silently — mark rows as `new`/`duplicate` by normalised phone or exact name, and let the user choose. Limit: 500 contacts, 1 MB.
- **Done when:** tests cover vCard 3.0 and 4.0, folded lines, a missing phone, duplicates, and the size limit.

### T9 — Brand accent colour on PDFs · S · after T7 (same files)
- **Files:** migration adding nullable `tenant.brand_color` (hex), Settings colour picker, PDF templates, tests.
- **Rules:** validate `^#[0-9a-fA-F]{6}$`; the default is the current orange. Text on the colour must stay readable (use dark text when the colour is light).

---

## 6. Review checklist (for the human, before merging an agent's branch)

- [ ] The diff touches only the files the task listed.
- [ ] No file from 3.2 #1 was changed; no new dependency beyond what the task allows.
- [ ] Every new query filters by `tenant_id` from the context; there is a cross-tenant test.
- [ ] Money is `Decimal`; GST goes only through `gst_calculator`.
- [ ] The migration has a `downgrade()` and new columns are nullable or defaulted.
- [ ] `pytest`, `npm run lint` and `npm run build` pass on your machine.
- [ ] Before showing it to anyone: `python backend/scripts/demo_preflight.py <url> --api-key <key>` prints READY.
