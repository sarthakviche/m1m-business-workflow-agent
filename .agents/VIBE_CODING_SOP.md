# Vibe Coding to Production — Standard Operating Procedure
**Version:** 1.0  
**Audience:** Solo builders, founding engineers, AI-first product teams  
**Stack:** Next.js · FastAPI · Supabase · Vercel · Antigravity · Claude Code  
**AI Roles:** Claude / GPT (planning, specs, docs) · Antigravity / Claude Code (execution)

---

## How to Use This Document

This SOP is a living document. Every new project starts by copying it into the repo root as `SOP.md`, then leaving it there. When you open a new coding agent session, you paste the relevant Phase section as context. The agent reads the conventions, the constraints, and the active checklist — and executes inside those guardrails. You never rely on the agent remembering any of this between sessions.

The SOP is also a thinking forcing function. The phases don't exist to slow you down. They exist because agents write fast and you think slowly, and if the thinking doesn't happen before the writing, you're debugging instead of shipping.

---

## Global Conventions

These apply across every phase, every file, every agent prompt. No exceptions.

### Repository Conventions

```
project-root/
├── .claude/                  # Claude Code skills and context
│   ├── AGENTS.md             # Agent instructions (auto-loaded by Claude Code)
│   └── skills/               # Custom skill files for this repo
├── .github/
│   └── workflows/
│       ├── ci.yml            # Lint + type-check + test on every PR
│       └── deploy.yml        # Deploy on merge to main
├── docs/
│   ├── ARCHITECTURE.md       # System design, ADRs, service boundaries
│   ├── CONSTRAINTS.md        # Per-feature constraint blocks (see Phase 3)
│   ├── DECISIONS.md          # Architecture Decision Records (ADRs)
│   └── API.md                # Endpoint reference, auth model, error codes
├── backend/                  # FastAPI service
│   ├── app/
│   │   ├── domains/          # One folder per business domain
│   │   │   └── <domain>/
│   │   │       ├── router.py       # HTTP layer only — no business logic
│   │   │       ├── service.py      # Business logic — no DB calls
│   │   │       ├── repository.py   # DB layer only — no logic
│   │   │       └── schemas.py      # Pydantic models for this domain
│   │   ├── core/
│   │   │   ├── config.py     # Settings via pydantic-settings
│   │   │   ├── security.py   # Auth helpers, JWT, scopes
│   │   │   ├── db.py         # DB session factory
│   │   │   ├── logging.py    # Structured logging config
│   │   │   └── errors.py     # Global exception handlers
│   │   └── main.py           # App factory, middleware, router registration
│   ├── tests/
│   │   ├── unit/             # Pure logic tests — no DB, no HTTP
│   │   └── integration/      # DB + HTTP via TestClient
│   ├── alembic/              # DB migrations
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                 # Next.js app
│   ├── app/                  # App Router
│   │   ├── (auth)/           # Route group: auth flows
│   │   ├── (dashboard)/      # Route group: authed app
│   │   └── api/              # Route handlers (lightweight — not business logic)
│   ├── components/
│   │   ├── ui/               # Primitives: Button, Input, Card, etc.
│   │   └── features/         # Domain-specific composites
│   ├── lib/
│   │   ├── api.ts            # Typed API client — all fetch calls live here
│   │   ├── auth.ts           # Auth helpers
│   │   └── utils.ts
│   ├── hooks/                # Custom React hooks
│   ├── types/                # Shared TypeScript types
│   └── public/
├── SOP.md                    # This file
├── .env.example              # All required env vars, no values
├── .gitignore
├── docker-compose.yml        # Local dev stack
└── README.md
```

### Naming Conventions

| Layer | Convention | Example |
|---|---|---|
| Python files | `snake_case` | `shipment_service.py` |
| Python classes | `PascalCase` | `ShipmentService` |
| Python functions | `snake_case` | `get_shipment_by_id` |
| TypeScript files | `kebab-case` | `shipment-card.tsx` |
| React components | `PascalCase` | `ShipmentCard` |
| React hooks | `camelCase`, prefix `use` | `useShipmentStatus` |
| DB tables | `snake_case`, plural | `shipments`, `compliance_checks` |
| DB columns | `snake_case` | `created_at`, `user_id` |
| Env vars | `SCREAMING_SNAKE_CASE` | `SUPABASE_URL` |
| API routes | `kebab-case`, versioned | `/api/v1/shipments` |
| Git branches | `type/short-description` | `feat/shipment-upload` |
| Commits | Conventional Commits | `feat: add shipment upload endpoint` |

### Git Commit Types
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code change with no behavior change
- `perf:` — performance improvement
- `test:` — adding or updating tests
- `docs:` — documentation only
- `chore:` — build scripts, dependencies, config
- `security:` — security fix or hardening

### Environment Variable Rules
1. Every secret lives in `.env` (never committed) or the deployment platform's secret store
2. `.env.example` lists every variable with a description comment and a fake/empty value
3. The app must fail loudly on startup if any required env var is missing — never silently default
4. No hardcoded URLs, keys, or secrets anywhere in code — ask the agent to grep before every merge

### Skills: What They Are and How to Use Them

A **skill** is a markdown file that tells a coding agent how to behave within a specific domain. It is not documentation for humans. It is context you deliberately inject into an agent so it stops making arbitrary decisions and starts making your decisions.

Skills live in `.claude/skills/` for Claude Code or as pinned files in Antigravity. You reference them explicitly in every agent prompt that needs them.

**Recommended skills to maintain in every repo:**

| Skill File | Purpose |
|---|---|
| `AGENTS.md` | Master instructions — loaded automatically by Claude Code. Covers repo structure, naming conventions, what the agent must never do, what to check before every write. |
| `skills/backend.md` | FastAPI conventions: domain structure, Pydantic validation rules, error handling patterns, auth middleware usage, how to write a new endpoint. |
| `skills/frontend.md` | Next.js conventions: server vs client component rules, data fetching patterns, performance rules, component structure. |
| `skills/database.md` | Supabase / PostgreSQL rules: never write raw SQL in service layer, RLS policy requirements, migration naming, index requirements for query patterns. |
| `skills/testing.md` | What to test, what not to test, test naming, how to mock external services, coverage floors. |
| `skills/security.md` | Auth checklist per endpoint type, input validation rules, rate limiting requirements, logging PII rules. |
| `skills/constraints.md` | Links to `docs/CONSTRAINTS.md` and explains how to read a constraint block before implementing any feature. |

**How to write a skill file — template:**

```markdown
# Skill: [Domain]
## What this skill governs
[One paragraph — what part of the codebase this covers]

## Rules the agent must follow
- [Specific, unambiguous rule]
- [Another rule]

## Patterns to use
[Code examples of the correct pattern]

## Patterns to never use
[Code examples of what not to do, and why]

## Before you write any code in this domain, check:
- [ ] Have you read the relevant constraint block in docs/CONSTRAINTS.md?
- [ ] Does this change touch more than one domain? If so, document the interface.
- [ ] [Domain-specific pre-flight check]
```

### Prompting Conventions

The quality of agent output is almost entirely determined by the quality of the prompt. These are the conventions — treat them as rules, not suggestions.

**Structure every agent prompt in this order:**

```
CONTEXT:
[What feature or area of the codebase is in scope. Paste the relevant skill file content here. Never assume the agent has read it.]

CONSTRAINT BLOCK:
[Paste the exact constraint block from docs/CONSTRAINTS.md for this feature. If a constraint block doesn't exist yet, write it before prompting.]

TASK:
[One specific, atomic task. If you have three things to do, send three prompts. Agents compound errors across big tasks — small scoped prompts produce cleaner code.]

BEFORE YOU WRITE ANY CODE:
[Ask the agent to produce an implementation plan first. Review the plan. Then say "proceed."]

DO NOT:
[Explicit prohibitions for this task. "Do not modify any other domain. Do not add any new dependencies without flagging them. Do not hardcode any values."]

VERIFICATION:
[Tell the agent exactly how you'll verify it's done. "This is complete when: the endpoint returns 200 with the documented response schema, a unit test covers the happy path, and the error case for missing auth returns 401 not 500."]
```

**Prompt anti-patterns to avoid:**
- "Build me a [feature]" — no constraints, agent invents everything
- "Refactor the whole backend" — too broad, agent breaks things you weren't watching
- "Make it production ready" — meaningless without specifying what that means for this feature
- Starting a new session without pasting the relevant skill and constraint block — agent has no memory, it will contradict decisions made in a prior session

---

## Phase 0: Idea Validation

**Intention:** Before a single line of planning exists, the idea must survive stress-testing. Most products fail not because of bad code but because they were solving a problem that either wasn't real, wasn't painful enough to pay for, or was already solved well enough by existing tools. This phase exists to catch that cheaply — with text, not code. The primary AI tool here is Claude or GPT in a chat interface, used as a ruthless critic, not a cheerleader. The output of this phase is a one-page problem statement and a falsifiable hypothesis. If you cannot produce those two things, you do not have an idea — you have a feeling, and you need to keep thinking.

### Checklist

- [ ] **Problem interview:** Write a 3-5 sentence description of the problem from the user's perspective — not the solution, only the problem. No product mentioned.
- [ ] **Existing solution audit:** Use Claude/GPT to list every existing tool that partially or fully solves this. Force-rank them. Write one sentence on why each fails the target user.
- [ ] **Falsifiable hypothesis:** State what would prove the idea wrong. Format: "If [target user] exists and has [problem], they will [observable behavior] within [timeframe] given [minimum version of the product]."
- [ ] **Anti-pitch:** Ask Claude: "What are the three most likely reasons this product fails in year one?" Write down the answers. If any are fatal, address them before proceeding.
- [ ] **Target user definition:** One specific, nameable type of person. Not "SMEs" — "a textile exporter in Surat with 5-20 employees who currently manages compliance in WhatsApp and Excel."
- [ ] **Scope gate:** Confirm the MVP tests the hypothesis without building anything extra. Write the one sentence that defines what the MVP must prove.

**AI tool:** Claude (chat) or GPT-4o  
**Deliverable:** `docs/PROBLEM_STATEMENT.md` — problem, hypothesis, anti-pitch answers, target user definition

---

## Phase 1: Feature Planning

**Intention:** Given a validated problem, decompose what needs to be built into a feature tree organized by user journey, not by technical layer. This is not a backlog dump. Every feature listed must pass a three-question gate: what user job does it do, is it actually required for the MVP hypothesis, and what is the absolute minimum version of it that still does the job. The failure mode this phase prevents is scope bloat — agents make feature bloat cheap because writing code feels like progress. Features that aren't in the MVP list don't get built yet, and that decision is made here, not mid-sprint. The planning AI tool (Claude/GPT) is useful here for catching missing features you haven't thought of — particularly operational features like account deletion, admin views, and error states that builders routinely forget until production.

### Checklist

- [ ] **User journey map:** Write the primary journey from a new user's first touch to the core value moment. Every step is a potential feature cluster.
- [ ] **Feature tree:** For each journey step, list features. Indent sub-features under parent features. Do not flatten into a list.
- [ ] **MVP gate per feature:** Mark each feature as MVP / Post-MVP / Nice-to-Have. A feature is MVP only if removing it makes the hypothesis untestable.
- [ ] **Forgotten feature check:** Ask Claude: "Given this product, what operational, edge case, or compliance features am I probably missing?" Add anything critical to the tree.
- [ ] **Dependency map:** Identify which features must exist before others can be built. Draw the DAG (even just in text). This becomes your build order.
- [ ] **Third-party dependency list:** For every feature that relies on an external API or service, note it explicitly. These are integration risks.
- [ ] **Feature spec stubs:** For every MVP feature, create a stub entry in `docs/CONSTRAINTS.md` with the feature name and a placeholder for the constraint block. This forces you to name every feature before Phase 3.

**AI tool:** Claude (chat) for the gap-fill exercise  
**Deliverable:** `docs/FEATURES.md` — feature tree with MVP labels, dependency map, third-party list

---

## Phase 2: Architecture

**Intention:** With the feature tree finalized, the architecture pass defines the system before any code is written. This phase produces the decisions that all future agent sessions must respect: service boundaries, database schema at a domain level, auth strategy, async job requirements, and the data flow between components. A coding agent without an architecture document will make these decisions itself — and it will make them inconsistently across sessions, because it has no memory. ARCHITECTURE.md is the agent's memory for structural decisions. An Architecture Decision Record (ADR) is written for every non-trivial choice so that future sessions — and future teammates — understand not just what was decided but why, and what alternatives were considered. This phase is done in conversation with Claude or GPT, never by an execution agent.

### Checklist

- [ ] **Service boundary definition:** List every service (frontend, backend, background workers, external APIs). For each, write one sentence on what it owns and what it never touches.
- [ ] **Database schema (domain level):** For each domain, list its core tables and the relationships between them. This is not the full schema — it's enough to catch bad data model decisions before they're built.
- [ ] **Auth strategy:** Pick one auth approach and document it completely: how sessions work, what tokens look like, what scopes exist, how refresh works, what happens on token expiry.
- [ ] **Async job identification:** Any operation that takes >500ms or depends on an external service is a background job candidate. List them. Specify the queue/worker strategy (e.g., Supabase Edge Functions, Celery, BullMQ).
- [ ] **ADR for every significant decision:** Format — Context / Decision / Alternatives Considered / Consequences. Minimum one ADR for: auth approach, database choice, background job strategy, AI provider choice.
- [ ] **ARCHITECTURE.md written and committed:** This file is the first thing committed to the repo. No feature branch is opened before it exists.
- [ ] **Skill files initialized:** Create `.claude/AGENTS.md` and stub out all skill files in `.claude/skills/`. Even empty stubs force you to fill them before the agent is invoked.
- [ ] **Environment variable inventory:** List every env var the system will need. Add them to `.env.example` now, not when the build breaks.

**AI tool:** Claude (chat) — architecture reasoning, ADR drafting  
**Deliverable:** `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `.claude/AGENTS.md`, skill file stubs

---

## Phase 3: Constraint Mapping

**Intention:** This is the highest-leverage phase in the entire SOP — and the most commonly skipped. For every MVP feature, write a constraint block before any code is written. A constraint block is not a specification in the traditional sense. It is a set of specific, verifiable statements about what the feature must do, what it must never do, what performance it must meet, who is allowed to access it, how it fails gracefully, and what data invariants it preserves. The agent reads this block before writing a single line. If the constraint block is vague, the agent fills the gaps with guesses — and those guesses will be wrong in ways that are expensive to fix later (security holes, race conditions, compliance failures, silent data corruption). Writing a constraint block for a feature typically takes 10-20 minutes. Debugging a feature that was built without one typically takes days. This phase transforms vibe coding into engineering.

### Constraint Block Template

Write one block per MVP feature. Store all blocks in `docs/CONSTRAINTS.md`.

```markdown
## Feature: [Feature Name]

### Functional Constraint
- Input: [Exact input — type, format, size limits, required vs optional fields]
- Output: [Exact output on success — shape, status code, fields returned]
- Success condition: [What must be true for this to be considered successful]
- Failure condition: [What must happen on each failure type — not "return an error" but the exact error shape]
- Edge cases: [List every non-happy-path scenario explicitly]

### Data Constraint
- Tables touched: [List every table this feature reads or writes]
- Invariants: [Statements that must always be true in the DB after this runs]
- Source of truth: [Which field/table is the canonical value for any derived data]
- Migration required: [Yes/No. If yes, what changes.]

### Performance Constraint
- Expected load: [p50 requests/sec in normal operation]
- Acceptable latency: [p95 response time in ms]
- At 10x load: [What degrades gracefully vs what breaks — and which is acceptable]
- Pagination: [Required? Page size? Cursor or offset?]
- Caching: [What can be cached? TTL? Invalidation strategy?]

### Security Constraint
- Auth required: [Yes/No. If yes — which roles, which scopes]
- Ownership check: [Can user A access user B's resource? How is this enforced?]
- Input sanitization: [What inputs are sanitized at what layer]
- Rate limit: [Requests per minute per user/IP]
- Audit log: [What events are logged, with what data, to where]

### Failure Constraint
- If DB is unavailable: [Return 503 with retry-after header / queue for retry / etc.]
- If external API is unavailable: [Specific fallback behavior — never "handle gracefully"]
- Timeout: [Hard timeout in ms on every external call]
- Retry policy: [Max retries, backoff strategy, idempotency consideration]
- Partial failure: [If this operation is multi-step, what happens if step 2 fails after step 1 succeeded?]
```

### Checklist

- [ ] **Constraint block written for every MVP feature:** No feature moves to Phase 4 without a complete block. Incomplete fields are not acceptable — if you don't know the answer, that's a decision to make now.
- [ ] **Invariants reviewed by a second pass:** Re-read every invariant statement. Ask Claude: "Given these invariants, what race condition or concurrent operation could violate them?"
- [ ] **Security constraint reviewed:** Confirm that auth and ownership checks are explicit per feature, not assumed from a global middleware. Ask Claude: "If I strip all middleware from this endpoint, what data can be accessed or modified without auth?"
- [ ] **Performance numbers are real:** Don't write "fast" or "low latency." Write actual numbers based on the target user base. If you don't know, estimate and document the assumption.
- [ ] **Failure paths are specific:** "Return an error" is not a failure constraint. "Return 503 with `{"error": "service_unavailable", "retry_after": 30}` and log the dependency name and error code to structured logs" is a failure constraint.
- [ ] **Skill file updated:** After completing constraint blocks, update `.claude/skills/constraints.md` to reference any new patterns or domain-specific rules discovered during this phase.

**AI tool:** Claude (chat) — invariant review, security review, edge case discovery  
**Deliverable:** `docs/CONSTRAINTS.md` — complete constraint block for every MVP feature

---

## Phase 4: Build Loop

**Intention:** This is where agents execute — and where most of the vibe coding actually happens. The build loop is not "open Antigravity and start talking." It is a structured per-feature cycle: read the constraint block, ask the agent to produce an implementation plan, review the plan against the constraints, approve, execute, review the output, write tests against the constraints (not the code), and mark the feature complete only when it satisfies every constraint statement. The agent is operating inside a tight context window — it does not remember previous sessions, it does not know what you decided in Phase 2 unless you tell it, and it will make up plausible-sounding decisions if you leave gaps. Your job in the build loop is not to type less — it's to maintain the quality gate that the agent cannot maintain for itself. The split between Antigravity and Claude Code is practical: Antigravity runs the tight implementation cycles (write, run, check, iterate) and Claude Code handles anything that requires deep architectural reasoning across multiple files or domains before writing a single line.

### Per-Feature Build Prompt Template

```
SKILL CONTEXT:
[Paste full content of the relevant skill files: backend.md, security.md, database.md as applicable]

ARCHITECTURE REFERENCE:
[Paste the relevant section of ARCHITECTURE.md — the service boundary and data model for this domain]

CONSTRAINT BLOCK:
[Paste the exact constraint block for this feature from docs/CONSTRAINTS.md]

TASK:
Implement [Feature Name] as described in the constraint block above.

BEFORE WRITING CODE:
Produce an implementation plan: which files you will create or modify, the function signatures you will add, the DB queries you will write, and how you will satisfy each constraint statement. Do not write any code until I confirm the plan.

DO NOT:
- Modify any domain other than [domain name]
- Add any dependency not already in pyproject.toml / package.json without listing it as a "required addition" in your plan
- Hardcode any value that belongs in config or environment variables
- Write a route that returns 200 on a failure condition
- Leave any external call without a timeout

VERIFICATION:
This task is complete when:
1. Every success and failure path in the constraint block returns the documented response
2. Auth and ownership checks are enforced at the router layer before the service is called
3. A unit test covers the happy path and at least two failure cases
4. Running the test suite produces no new failures
```

### Backend Build Checklist (per feature)

- [ ] **Router:** HTTP concerns only. Calls service. Returns typed response. No business logic.
- [ ] **Service:** Business logic only. Calls repository. No direct DB access. No HTTP concepts.
- [ ] **Repository:** DB calls only. Parameterized queries or ORM. No logic beyond query construction.
- [ ] **Schemas:** Pydantic models for every request and response. Strict types — no `Any`, no bare `dict`.
- [ ] **Auth enforced:** Dependency injected at router level. Service never receives unverified user identity.
- [ ] **Ownership check:** If a resource belongs to a user, the repository checks `user_id = current_user.id` — not the service, not the router.
- [ ] **Error handling:** Domain exceptions defined in `core/errors.py`. Service raises domain exceptions. Global handler converts them to HTTP responses.
- [ ] **Timeout on all external calls:** Every `httpx`, every LLM call, every third-party API call has an explicit timeout.
- [ ] **Structured logging:** Every significant event logged with `logger.info()` / `logger.error()` using key-value fields, not f-strings with concatenated values.
- [ ] **Tests written:** Unit tests in `tests/unit/` for service logic. Integration tests in `tests/integration/` for router + DB together.

### Frontend Build Checklist (per feature)

- [ ] **Server component by default:** Every component is a server component unless it explicitly needs browser APIs or event handlers.
- [ ] **Client components minimized:** Client components are leaf nodes — they receive data as props, they do not fetch.
- [ ] **All fetch calls in `lib/api.ts`:** No inline `fetch()` in components. The API client is typed and centralized.
- [ ] **Loading states handled:** Every async boundary has a loading skeleton, not a blank screen.
- [ ] **Error states handled:** Every async boundary has an error state that tells the user what happened and what to do, not just "something went wrong."
- [ ] **Empty states handled:** Every list or data view has an empty state design.
- [ ] **No layout shift:** Images use `next/image` with explicit `width`/`height`. Dynamic content areas have fixed or min-height.
- [ ] **Dynamic imports for heavy components:** Charts, editors, rich text — anything not needed on initial render uses `dynamic(() => import(...), { ssr: false })`.
- [ ] **Lighthouse score checked:** Before marking a page complete, run Lighthouse. Performance < 85 requires investigation.
- [ ] **Types shared:** API response types live in `types/` and are imported by both the API client and the components. No duplicated interface definitions.

### Code Review Checklist (self-review before any merge)

Run this before merging any feature branch, whether you wrote the code or an agent did:

- [ ] `grep -r "TODO\|FIXME\|HACK\|hardcoded\|password\|secret\|api_key" .` returns nothing unexpected
- [ ] No new `Any` types in TypeScript without a comment explaining why
- [ ] Every new endpoint has a corresponding test
- [ ] Migration file exists if any schema changed
- [ ] `.env.example` updated if any new env var was added
- [ ] The constraint block's failure paths are actually implemented, not just the happy path
- [ ] Rate limiting is applied to any public or user-facing endpoint

**AI tool:** Antigravity (implementation loop), Claude Code (architectural changes, multi-file refactors)  
**Deliverable:** Working feature branch that satisfies every line of its constraint block

---

## Phase 5: Security Hardening Pass

**Intention:** Security is not a feature — it is a property of the system, and it does not emerge automatically from adding an auth library. This phase is a dedicated, structured review that happens before any deployment, not as part of feature work. Security work done during feature work is always incomplete because the mental model is on the feature, not the attack surface. In a vibe-coded codebase, this pass is even more critical because agents will happily implement a plausible-looking auth check that has a subtle bypass, or leave a route unguarded because no prompt told it that route was sensitive. This phase uses Claude (chat) as an auditor — you paste sections of code and ask it to attack them, not review them politely.

### Checklist

- [ ] **Endpoint audit:** List every route in the backend. For each, confirm: is auth required (by design), is auth enforced (in code), is ownership checked if the resource belongs to a user.
- [ ] **Input validation audit:** Every endpoint that accepts user input validates it with Pydantic at the router boundary. No raw user input reaches the service or repository layer.
- [ ] **SQL injection check:** If any repository uses string interpolation in queries, replace with parameterized queries. Ask the agent to grep for f-string SQL.
- [ ] **Secret scan:** Run `git log --all --full-history -- "*.env"` and `grep -r "sk-\|Bearer \|password=" .` on the working tree.
- [ ] **CORS configuration:** Confirm allowed origins are explicitly listed, not `*`.
- [ ] **Rate limiting:** Every public endpoint (auth, signup, password reset, contact) has rate limiting. Authenticated endpoints have per-user limits.
- [ ] **RLS policies on Supabase:** Every table accessed by client-side code has Row Level Security enabled and tested. The test is: query the table without auth and confirm it returns nothing.
- [ ] **Dependency vulnerability scan:** Run `pip-audit` (Python) and `npm audit` (Node). Address any high/critical findings before deployment.
- [ ] **HTTPS enforced:** Backend rejects HTTP requests at the infrastructure level, not the application level.
- [ ] **Sensitive data in logs:** Grep for any logging of passwords, tokens, PII. Remove or redact.

**AI tool:** Claude (chat) — paste code sections and ask "how would you attack this, what can be bypassed?"  
**Deliverable:** Updated code with all findings addressed, security audit log in `docs/SECURITY_AUDIT.md`

---

## Phase 6: Performance Pass

**Intention:** Performance problems in vibe-coded applications follow a predictable pattern: N+1 database queries, missing pagination, synchronous long-running operations, unoptimized images, and client-side waterfalls. Agents produce these not because they are bad at writing fast code, but because no prompt told them the performance constraint. This phase forces a structured review of the most common failure modes before they reach production. The target is not micro-optimized code — it is code without obvious anti-patterns that would fail under modest real-world load.

### Checklist

- [ ] **Query analysis:** For every list endpoint, confirm: is it paginated, does it have appropriate indexes, is it doing a join that could be an N+1. Run `EXPLAIN ANALYZE` on any query that touches more than one table.
- [ ] **Index audit:** Every foreign key column has an index. Every column used in a `WHERE` clause in a frequent query has an index. Supabase Dashboard → Table Editor → Indexes.
- [ ] **Background job validation:** Any operation that calls an external API, sends an email, or runs an LLM is not in the request/response cycle. It is in a background job.
- [ ] **Caching inventory:** List what is cached, the TTL, and the invalidation strategy. Nothing is cached without an invalidation strategy.
- [ ] **Frontend bundle analysis:** Run `next build` and check the bundle size output. Any route with > 200kb JavaScript is investigated.
- [ ] **Image optimization:** Every `<img>` tag is replaced with `<Image>` from `next/image`. No exceptions.
- [ ] **Server component audit:** Review every `"use client"` directive. If the component doesn't use hooks or browser APIs, remove the directive.
- [ ] **Lighthouse baseline:** Run Lighthouse on the three most important pages. Record scores. Performance < 85 is a blocker.

**AI tool:** Claude Code — paste slow queries and ask for index recommendations and query rewrites  
**Deliverable:** Performance baseline recorded in `docs/PERFORMANCE.md`, index migrations applied

---

## Phase 7: Deployment and Observability

**Intention:** Deployment is not the end of the SOP — it is the beginning of the feedback loop. A feature in production that nobody watches is not a deployed feature, it is a liability. This phase establishes the minimum observability stack so that when something breaks (it will), you know within minutes, not days. It also establishes the CI/CD pipeline so that future agent-built features can only reach production by passing the full test suite. The goal is not a perfect deployment pipeline — it is a deployment pipeline that prevents the most common ways a vibe-coded update breaks production.

### Checklist

- [ ] **CI/CD pipeline:** GitHub Actions runs on every PR: lint (`ruff`, `eslint`), type-check (`mypy`, `tsc --noEmit`), full test suite. Deploy to production triggers only on merge to `main` after all checks pass.
- [ ] **Environment parity:** Staging environment exists with production config (not development config). All deployments go to staging first.
- [ ] **Error tracking:** Sentry (free tier) installed on both backend and frontend. Every unhandled exception creates an alert.
- [ ] **Structured logging:** Backend logs to stdout in JSON format. Each log line has `timestamp`, `level`, `message`, `trace_id`, and any relevant domain fields. No print statements in production code.
- [ ] **Health check endpoint:** `GET /api/v1/health` returns `{"status": "ok", "db": "ok", "version": "..."}`. Returns 503 if DB is unreachable. This is what your deployment platform monitors.
- [ ] **Uptime monitoring:** Use UptimeRobot (free tier) on the health check endpoint. Alert on any 5-minute outage window.
- [ ] **Analytics baseline:** PostHog (free tier) installed on frontend. At minimum: page views, feature usage events for every core feature, and error events.
- [ ] **Rollback documented:** Document the one-command rollback procedure. Test it before you need it.
- [ ] **`README.md` accurate:** Local setup instructions tested from scratch on a clean environment. If a new engineer can't run the project in 15 minutes following the README, the README is wrong.

**AI tool:** Claude Code — CI/CD YAML generation, Dockerfile review  
**Deliverable:** Working CI/CD pipeline, Sentry + PostHog integrated, health check live

---

## Appendix A: AI Tool Quick Reference

| Task | Tool | Prompt Start |
|---|---|---|
| Stress-test an idea | Claude chat | "Argue against this product idea. Three reasons it fails." |
| Write a PRD | Claude chat / GPT-4o | "Given this problem statement and feature list, write a PRD..." |
| Write an ADR | Claude chat | "I'm deciding between X and Y for [decision]. Help me write an ADR covering context, decision, alternatives, and consequences." |
| Write a constraint block | Claude chat | "I'm building [feature]. Help me fill in this constraint template..." |
| Implement a feature | Antigravity | Use Per-Feature Build Prompt Template above |
| Refactor across multiple files | Claude Code | Use Per-Feature Build Prompt Template, add "reason about the full impact before writing" |
| Security audit | Claude chat | "Here is this endpoint's code. How would you attack it? What can be bypassed?" |
| Write documentation | Claude chat / GPT-4o | "Write API documentation for these endpoints in the format of [target doc]" |
| Write slide content | Claude chat | "Given this architecture, write slide content for a technical overview deck. Audience: [audience]." |
| Debug a production error | Claude Code | Paste error + stack trace + relevant code. Ask "What is the most likely root cause and what is the minimal fix?" |

---

## Appendix B: Free Tier Stack Reference

| Service | Purpose | Free Tier Limit | When to Upgrade |
|---|---|---|---|
| Supabase | DB + Auth + Storage | 500MB DB, 50MB storage, 50k MAU auth | 50k active users or 500MB data |
| Vercel | Frontend hosting | 100GB bandwidth, unlimited deployments | Significant traffic or team size |
| Render | FastAPI backend | 512MB RAM, sleeps after inactivity | Any production traffic that can't tolerate cold starts |
| Railway | FastAPI backend (alt) | $5 credit/month, no sleep | More reliable than Render free for persistent services |
| GitHub Actions | CI/CD | 2,000 min/month | Heavy test suites |
| Sentry | Error tracking | 5,000 errors/month | Any meaningful production usage |
| PostHog | Analytics | 1M events/month | Significant scale |
| UptimeRobot | Uptime monitoring | 50 monitors, 5-min intervals | Never — free is sufficient |
| Antigravity | Coding agent | Gemini 3 free tier included | When repo complexity warrants Claude models |

---

## Appendix C: AGENTS.md Master Template

Copy this into `.claude/AGENTS.md` at repo initialization. This file is auto-loaded by Claude Code at the start of every session.

```markdown
# Agent Instructions — [Project Name]

## What this project is
[One paragraph. What the product does, who it's for, what problem it solves.]

## Tech stack
- Backend: FastAPI + Python 3.12 + Pydantic v2 + SQLAlchemy 2.0
- Database: PostgreSQL via Supabase
- Frontend: Next.js 14 (App Router) + TypeScript + Tailwind
- Auth: Supabase Auth (JWT)
- Deployment: Vercel (frontend), Render (backend)

## Repository structure
[Paste the folder tree from the Global Conventions section above]

## Before you write any code
1. Read the relevant skill file in .claude/skills/
2. Read the constraint block for this feature in docs/CONSTRAINTS.md
3. Produce an implementation plan and wait for approval

## Rules you must never break
- Business logic never lives in router.py
- DB calls never live in service.py
- No hardcoded secrets, URLs, or environment-specific values
- No new dependency added without flagging it in the implementation plan
- Every external call has an explicit timeout
- Every route that returns user data checks ownership against the authenticated user
- No print() in production code — use the logger

## When you're unsure
State the uncertainty explicitly and propose two options with their tradeoffs. Do not make a silent choice on a decision that affects architecture, security, or data integrity.
```

---

*This SOP is a living document. Update it when a decision is reversed, a new pattern is established, or a phase checklist proves incomplete. The cost of an outdated SOP is an agent that makes decisions you've already decided differently.*
