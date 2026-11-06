# Munim — Production Readiness Checklist

**Goal:** any Indian SME can sign up, onboard and run its own quotations and invoices, with its data isolated from every other business, on infrastructure that costs ₹0 until revenue justifies otherwise.

**Legend:** `[x]` done and verified · `[~]` built, but not yet proven on the live hosts · `[ ]` not started

**Priority:**
- **P0** blocks letting a second business on the platform
- **P1** needed before public launch
- **P2** needed soon after launch

**Progress (2026-11-06):** Phases 0 and most of Phase 1 are built. 320 backend tests pass on real Postgres, including real concurrency tests. The Supabase schema is applied and locked down. What's left for going live needs your accounts: see "What I need from you" in the [plan](./IMPLEMENTATION_PLAN.md).

**Biggest gap:** the app has never run on Render against Supabase, a real signup hasn't happened yet, and the Docker image hasn't been built.

---

## 1. Identity and multi-tenancy

| Pri | Item | Status |
|---|---|---|
| P0 | Sign up, log in and log out for business owners | [~] real Supabase wired up; needs one real signup |
| P0 | Backend verifies a signed token on every request | [x] including live key fetch and a forged-token test against real Supabase |
| P0 | A new signup creates its own business (tenant) | [x] |
| P0 | Onboarding state lives on the server, not in `localStorage` | [x] |
| P0 | Requests with no credentials are rejected outside local dev | [x] |
| P0 | Automated cross-tenant isolation tests on every endpoint | [x] new routes are swept automatically |
| P0 | Tables can't be read through Supabase's public API | [x] all 21 tables return 401 with the public key |
| P1 | Password reset and email verification | [~] screens built; needs custom SMTP |
| P1 | Google sign-in | [~] button built, hidden until configured |
| P1 | Per-user Row-Level Security policies inside Postgres | [ ] today RLS blocks the public API; the backend is still trusted to filter by tenant |
| P2 | Invite staff and accountants, with role enforcement | [ ] |
| P2 | Audit log of who created or changed what | [ ] |
| P2 | One login across several businesses (for accountants) | [ ] |

## 2. Security

| Pri | Item | Status |
|---|---|---|
| P0 | PDF downloads require auth and an ownership check | [x] |
| P0 | App fails closed if `ENV` is unset | [x] |
| P0 | App refuses to boot in production with missing or unsafe config | [x] |
| P0 | CORS origins come from config, and `PATCH` and `Authorization` are allowed | [x] |
| P0 | Secrets never committed (`.env` has never been in git history) | [x] |
| P0 | `m1m.db` removed from git and ignored | [~] staged, not committed. Old copies remain in git history (demo data only) |
| P1 | Per-IP rate limits on chat, upload and signup endpoints | [x] |
| P1 | TLS certificate verification on the database connection (today encrypted, not verified) | [ ] |
| P1 | Security headers | [x] API and web app |
| P1 | Upload content sniffing (today trusts the declared type) | [ ] |
| P1 | Dependency and secret scanning in CI | [ ] |
| P2 | Move API keys from an env var to a hashed, per-tenant table | [ ] |

## 3. Data and reliability

| Pri | Item | Status |
|---|---|---|
| P0 | Runs on Postgres, with migrations applied automatically on deploy | [~] full suite passes on Postgres and schema is on Supabase; not yet deployed |
| P0 | PDFs stored durably | [x] in Postgres, in the same transaction as the document |
| P0 | Writes commit before the API responds, and failed requests are fully undone | [x] |
| P0 | Invoice numbers can't collide or skip | [x] tested with 20 simultaneous requests |
| P0 | Stock can't be oversold by simultaneous invoices | [x] |
| P0 | A quotation can't be converted twice | [x] |
| P1 | Never send a text-only fallback PDF in production | [x] the document fails and rolls back instead |
| P1 | Nightly encrypted database backup, plus one rehearsed restore | [~] workflow written; needs secrets, a first run and a rehearsal |
| P1 | Duplicate protection for retried chat requests (idempotency keys are sent but unused) | [ ] |
| P1 | Durable Telegram processing (work is lost if the instance restarts mid-task) | [ ] the keep-warm ping reduces this |
| P1 | Connection pool sized for the Supabase pooler | [~] small, configurable pool; not load-tested |
| P2 | Pagination on documents, customers and items | [ ] |
| P2 | Stale conversation and link-code cleanup job | [ ] |

## 4. AI cost and abuse control

| Pri | Item | Status |
|---|---|---|
| P0 | Per-business and overall daily AI limits | [x] |
| P0 | Clear message when AI is limited, falling back to the rule-based parser | [x] |
| P1 | Decide on free vs paid Gemini before real customer data goes in (see plan) | [ ] **your decision** |
| P1 | Disclose AI sub-processors in the privacy policy | [ ] |
| P2 | Usage dashboard per business | [ ] |

## 5. Indian compliance and legal

| Pri | Item | Status |
|---|---|---|
| P0 | Invoice fields reviewed against GST Rule 46 by a CA | [ ] **needs a CA** |
| P1 | Terms of Service and Privacy Policy (DPDP Act 2023), accepted at signup | [ ] |
| P1 | Issued invoices are immutable, corrected only through credit notes | [ ] |
| P1 | Invoice numbering reviewed for financial-year rules | [ ] numbers currently restart monthly |
| P1 | Tenant data export and account deletion | [ ] |
| P2 | Retention policy (GST records are kept for about 6 years) | [ ] |
| P2 | Credit and debit notes, HSN summary | [ ] |

## 6. Observability and operations

| Pri | Item | Status |
|---|---|---|
| P0 | Liveness and readiness endpoints (readiness checks the database) | [x] |
| P0 | Unhandled errors return a safe JSON error, never a stack trace | [x] |
| P0 | Request ID on every log line and response | [x] |
| P1 | Structured JSON logs without customer data | [~] JSON done; log contents still need a privacy review |
| P1 | Sentry error tracking | [~] backend ready, needs a DSN; frontend not started |
| P1 | Uptime monitor with alerts (also keeps the free instance warm) | [ ] **needs your account** |
| P1 | Runbook: deploy, rollback, restore, rotate secrets | [~] [deployment guide](./DEPLOYMENT.md) covers deploy and restore |
| P2 | Basic product metrics (signups, documents per week) | [ ] |

## 7. Engineering and delivery

| Pri | Item | Status |
|---|---|---|
| P0 | Tests run against a throwaway database, built from the real migrations | [x] |
| P0 | CI on every push: tests on SQLite and Postgres, frontend lint and build | [~] written; first run happens on push |
| P0 | Production Docker image: non-root, no test dependencies, runs migrations | [~] written; not built here because Docker wasn't running. CI builds it |
| P0 | Infrastructure as code for the hosts (`render.yaml`, Pages config) | [~] written; not yet deployed |
| P1 | CI also runs tests on real Postgres | [~] written; verified locally on Postgres 16 (Supabase and CI run 17) |
| P1 | Pinned dependency versions | [ ] |
| P1 | Staging environment, with `main` as production | [ ] |
| P1 | End-to-end smoke test of signup through to invoice | [~] API-level test in CI; no browser test yet |
| P1 | Frontend tests (there are none today) | [ ] |
| P2 | Remove leftover scripts (`refactor*.py`, `check_*.py`), unused stubs, and duplicate `api/*.py` and `agents/` modules | [ ] |
| P2 | Fix remaining inaccurate README claims (missing LICENSE and MVP doc) | [ ] |

## 8. Product polish

| Pri | Item | Status |
|---|---|---|
| P0 | Login and signup screens | [x] |
| P0 | Sign out, and handling of expired sessions | [x] |
| P0 | App-wide error boundary instead of a white screen | [x] |
| P0 | Edit business details after onboarding | [x] |
| P0 | Real logo everywhere, and a designed sign-up page | [x] |
| P1 | Public landing page with pricing ("free") and legal links | [ ] |
| P1 | Loading, empty and error states audited on every screen | [ ] |
| P1 | Add, edit and delete for customers and items without going through chat | [ ] |
| P1 | Record payments and mark invoices paid (dashboard figures need this) | [ ] |
| P1 | Business logo and bank/UPI details on documents | [ ] |
| P1 | Telegram linking discoverable in onboarding | [ ] |
| P1 | Accessibility pass (keyboard, labels, contrast) | [ ] |
| P2 | Document search and filters | [ ] |
| P2 | Share an invoice by public signed link | [ ] |
| P2 | Hindi UI | [ ] |
| P2 | WhatsApp channel (the official API is not free, see plan) | [ ] |
