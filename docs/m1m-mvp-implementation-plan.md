# Implementation Plan — M1M MVP
### Step-by-step, for handoff to a coding agent + a manual setup checklist for you
**Companion to:** `m1m-mvp-prd.md` (what/why) and `m1m-mvp-trd.md` (full technical spec). This document is the *execution order* — what gets set up first, in what sequence the coding agent should build, and where the free-tier limits actually sit.

---

## Part A — Manual Setup (you do this, before the coding agent starts)

A coding agent can write every line of application code, but it cannot create accounts, click "I agree," or receive an OTP on your phone. These steps are yours, in this order, and should take under an hour total.

### A.1 — Supabase (database + auth + storage)
1. Go to supabase.com, sign up (no card required).
2. Create a new project — name it `m1m-mvp` or similar.
3. **Region matters:** pick a region close to India (Singapore is usually closest) for lower latency.
4. Once created, go to `Project Settings → API` and copy:
   - `Project URL` → this becomes `SUPABASE_URL`
   - `service_role` key (NOT the `anon` key — the backend needs the service role key; never expose it to the frontend) → this becomes `SUPABASE_SERVICE_ROLE_KEY`
5. Go to `Project Settings → Database` and copy the connection string → this becomes `DATABASE_URL` (use the "connection pooling" string, not the direct one, for the app's runtime connection).
6. **Free tier reality check:** <cite index="141-1">Supabase's free tier gives 500MB database storage, 1GB file storage, 50,000 monthly active users, and 5GB bandwidth — more than enough for an MVP pilot — but free projects pause automatically after 7 days of zero activity, with roughly a 60-second cold start when you manually resume them from the dashboard.</cite> This is fine for development, but **do this the morning of any demo or pilot check-in:** open the Supabase dashboard and confirm the project isn't paused, 30+ minutes beforehand.

### A.2 — Meta / WhatsApp Cloud API
1. Go to developers.facebook.com, create a developer account if you don't have one.
2. Create a new App → choose "Business" type → add the "WhatsApp" product to it.
3. Meta auto-provisions a **test phone number** and a **test access token** — this is what you'll use for the entire MVP build, no business verification needed.
4. Under the WhatsApp product's "API Setup" page, note down:
   - `Phone Number ID` → this becomes `WHATSAPP_PHONE_NUMBER_ID`
   - `Temporary access token` → this becomes `WHATSAPP_CLOUD_API_TOKEN` (this token expires in 24 hours by default — generate a **permanent token** instead: go to `System Users` under Business Settings, create a system user, assign it to the app, generate a token with `whatsapp_business_messaging` permission, set expiration to "Never")
5. Under "API Setup," add up to 5 **recipient test numbers** (your own phone, a teammate's, an investor's if you want them to try it live) — verify each by entering the OTP sent to that number.
6. Set a `WHATSAPP_VERIFY_TOKEN` yourself — any random string you make up (e.g., generate one with `openssl rand -hex 16`) — you'll enter this same value in both your `.env` file and Meta's webhook configuration screen; Meta uses it to confirm the webhook URL belongs to you.
7. **Don't configure the webhook URL yet** — you need a running server first (Part B will tell the coding agent to give you a local ngrok URL, or a deployed URL, to paste in here).

### A.3 — LLM API (Gemini)
1. Go to aistudio.google.com, sign in with a Google account.
2. Click "Get API key" → create a key → this becomes `GEMINI_API_KEY`.
3. <cite index="123-1">Free tier: 15 requests/minute, 1,500 requests/day, 1 million tokens/minute — no credit card required, no expiration.</cite> This comfortably covers development, testing, and demo usage. If you ever see rate-limit errors during heavy testing, that's the 15/minute ceiling — just slow down, don't panic.

### A.4 — GitHub
1. Create a new private repository for the project.
2. This is where the coding agent will push code, and where GitHub Actions (free for public repos, and free for private repos up to 2,000 minutes/month) will run tests.

### A.5 — Deployment accounts (only needed once you're past local development — see Part B, Phase 6)
1. **Render** (backend hosting): sign up at render.com, no card required for the free web service tier. <cite index="2-1">Render's free web service instance has 512 MB RAM and 0.1 CPU, and spins down after 15 minutes without traffic, taking 30-60 seconds to wake back up on the next request.</cite> This is genuinely fine for a pilot with light usage, but **do not use Render's free Postgres** — <cite index="8-1">Render's free database gets deleted after 30 days with no warning</cite>. Use Supabase (Part A.1) as your only database; Render free tier is for the backend app process only.
2. **Vercel** (frontend hosting): sign up at vercel.com, no card required. <cite index="3-1">The free Hobby tier includes static hosting on a global edge network with 100GB of bandwidth per month.</cite> This is far more than an MVP pilot needs.

### A.6 — Full list of secrets to hand to the coding agent
Once you've completed A.1–A.3, you'll have these seven values ready to drop into `.env` (never commit this file):
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=
GEMINI_API_KEY=
WHATSAPP_CLOUD_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
```
Two more you generate yourself, no external account needed:
```
JWT_SECRET=            # run: openssl rand -hex 32
ENV=development
```

**Total cost of everything in Part A: ₹0.** No step above requires a credit card.

---

## Part B — Build Sequence for the Coding Agent

Give the coding agent the PRD, the TRD, and this document together. Build in this order — each phase should be a working, testable checkpoint before moving to the next; do not let the agent jump ahead to Phase 4 with Phase 2 half-working.

### Phase 0 — Repo & environment scaffolding (½ day)
- Initialize repo structure per TRD Section 1.
- Set up `requirements.txt` / `package.json` with pinned versions per TRD Section 2.
- Create `.env.example` (values blank) and confirm `.env` is gitignored.
- Set up Alembic for migrations; write and run the initial migration from TRD Section 4's DDL.
- **Checkpoint:** `alembic upgrade head` runs clean against the Supabase `DATABASE_URL`; you can see the empty tables in the Supabase dashboard's Table Editor.

### Phase 1 — Auth + tenant scaffolding (1 day)
- Implement `/auth/otp/request` and `/auth/otp/verify` (TRD Section 9) — for MVP, send the OTP as a WhatsApp template message using the same Cloud API credentials, so you don't need a separate SMS vendor.
- Implement the JWT session issuance and the FastAPI dependency that sets `app.current_tenant_id` per request (TRD Section 4 RLS note) — this is the most important single piece of code in the whole project from a safety standpoint, build it early and test it early.
- **Checkpoint:** you can request an OTP on your own phone, verify it, and get back a session token. Write the cross-tenant RLS test now, before any real feature exists — it's easier to verify isolation on an empty schema than to retrofit it later.

### Phase 2 — GST calculator + PDF pipeline, in isolation (1 day)
- Build `gst_calculator.py` exactly per TRD Section 6, with its full unit test suite, **before** wiring it into any agent — this is pure logic, no LLM, no database, easiest to get bulletproof in isolation.
- Build the Jinja2 templates + WeasyPrint rendering pipeline, tested against hardcoded sample data (not agent-generated yet).
- **Checkpoint:** running a script with hardcoded line items produces a correctly formatted, correctly taxed PDF on disk.

### Phase 3 — Onboarding (1–1.5 days)
- Business profile endpoint, manual item/customer entry endpoints, CSV validation + bulk-upload/bulk-confirm endpoints (TRD Sections 8–9).
- **Checkpoint:** you can create a tenant, set its GST profile, and populate it with items/customers via all three paths described in the PRD (manual, CSV, and — this one can be a thin stub for now — WhatsApp-forwarded file).

### Phase 4 — Agent orchestrator + first two agents: Quotation, Invoice (2 days)
- Build the LangGraph state machine, intent classifier, and tool contracts per TRD Section 5.
- Wire Quotation Agent first (simpler — no tax calc, no stock decrement), then Invoice Agent (reuses the GST calculator from Phase 2 and the stock table).
- **Checkpoint:** via a direct API call to `/chat/message` (not WhatsApp yet — test the brain before testing the channel), "Quotation for X, 10 units of Y" produces a correct quotation, and "convert to invoice" produces a correctly taxed invoice PDF.

### Phase 5 — Stock Agent + Dues Agent (1 day)
- These are simpler reads/writes riding on the same orchestrator — should go faster now that the pattern is established in Phase 4.
- **Checkpoint:** stock level query returns correct numbers and reflects the decrement from Phase 4's invoice test; dues query correctly lists the unpaid invoice created in Phase 4.

### Phase 6 — WhatsApp channel wiring (1 day)
- Implement `/webhooks/whatsapp` per TRD Section 9, including signature verification.
- **Now go back to Part A.2, step 7:** run the server locally, tunnel it with ngrok (`ngrok http 8000`), paste the resulting HTTPS URL + your `WHATSAPP_VERIFY_TOKEN` into Meta's webhook config screen, and subscribe to the `messages` webhook field.
- **Checkpoint:** send "How much stock do I have for Y" from your actual WhatsApp app to the test number, and get a real reply. This is the first moment the whole thing feels real — don't skip celebrating it, but also don't skip re-testing the RLS boundary here since this is the first time an external, less-controlled input path exists.

### Phase 7 — Web app frontend (2–3 days, can partially overlap with Phase 4–6 if you have two people)
- Login, onboarding wizard, dashboard, chat panel, documents/customers/inventory tabs per TRD Section 10.
- The chat panel talks to `/chat/message` — the same endpoint the agent already works with, so this phase is mostly UI, not new backend logic.
- **Checkpoint:** a message sent from the web chat panel and a message sent from WhatsApp both show up in the same conversation history, for the same tenant.

### Phase 8 — Deployment (½–1 day)
- Push backend to Render (Part A.5), frontend to Vercel, update the Meta webhook URL to point at the Render URL instead of ngrok, set all production env vars in Render's dashboard (never in code).
- **Checkpoint:** the whole flow works with your laptop closed — message the WhatsApp number from your phone with your laptop off, and see it respond, proving it's actually running in the cloud, not on your machine.

### Phase 9 — Hardening pass before showing to real pilot businesses (1–2 days)
- Run through TRD Section 14's security checklist item by item.
- Run through TRD Section 15's per-feature acceptance criteria item by item.
- Load in one or two realistic full catalogs (via CSV) from businesses similar to your actual pilot targets, not just clean test data — this is where you'll find the fuzzy-matching and edge-case bugs that clean test data never surfaces.

**Total estimated build time: 10–13 working days**, consistent with the earlier PRD's estimate, now broken into checkpointed phases so a coding agent (or you reviewing its output) always knows exactly what "done" looks like before moving on.

---

## Part C — Free Tier Summary Table (what to watch, across the whole build)

| Service | Free tier ceiling | What happens if you exceed it | Risk level for MVP |
|---|---|---|---|
| Supabase | <cite index="141-1">500MB DB, 1GB storage, 50K MAU, 5GB bandwidth, pauses after 7 days idle</cite> | Project pauses (recoverable, not deleted) or read-only lock near storage cap | Low — just remember to check it's awake before any demo |
| Meta WhatsApp Cloud API (test mode) | <cite index="124-1">Unlimited free messages to 5 verified recipient numbers</cite> | You simply can't message a 6th number until you go through business verification | Low for MVP/pilot with a small test group |
| Gemini API | <cite index="123-1">15 RPM, 1,500 RPD, 1M TPM, no card, no expiry</cite> | 429 rate-limit error, resolves itself after a minute | Very low |
| Render (backend) | 512MB RAM, 0.1 CPU, sleeps after 15 min idle, ~30-60s cold start on wake | Slow first response after idle period, not a failure | Medium — a pilot business messaging after a quiet period will notice the delay; acceptable for MVP, revisit before a hard funding-critical live demo (or keep something pinging it every 10 minutes to prevent sleep, at zero cost, via a free uptime-monitor service) |
| Vercel (frontend) | <cite index="3-1">100GB bandwidth/month, 5-minute serverless function timeout</cite> | Won't be hit at MVP scale | Very low |
| GitHub Actions | 2,000 free minutes/month (private repos) | CI stops running until next month's quota resets | Very low at this project size |

**Bottom line: the entire MVP — development, WhatsApp integration, LLM calls, hosting, and a live pilot with a handful of real businesses — can run at ₹0/month.** The one operational habit worth building now: if you have a demo or investor meeting, ping the Supabase project and the Render backend 15–20 minutes beforehand so neither is cold-starting while someone's watching.

---

*Hand this document, the PRD, and the TRD to the coding agent together. This document tells it the order and the checkpoints; the TRD tells it exactly what to build at each step; the PRD tells it why, if it ever needs to make a judgment call not covered explicitly.*
