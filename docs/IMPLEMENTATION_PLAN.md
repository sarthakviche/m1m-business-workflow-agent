# Munim — Implementation Plan: One Business to Multi-Tenant SaaS

**Status:** in progress · **Written:** 2026-11-06 · **Tracked in:** [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md)

## Where we are

The core product is good. GST maths is deterministic, the agent flow works, the Telegram channel is well designed, and queries are consistently scoped by `tenant_id`. The schema is already multi-tenant.

What's missing is everything around it. There is no concept of a user, so the app always acts as one hardcoded business. Three things would cause real harm if we opened it up today:

1. **Anyone can read any invoice.** `GET /documents/{tenant}/{type}/{file}` has no auth.
2. **Forgetting one env var disables auth.** `ENV` defaults to `development`, which falls back to the demo tenant with no credentials.
3. **Documents would vanish.** Free hosts wipe the local disk on restart, and PDFs live there.

## Architecture decisions

Free-tier figures below come from research on 2026-11-06, much of it third-party. Check them against the official pricing pages when signing up, because these limits change often.

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | Database | **Supabase Postgres** (Mumbai) | Already used for `m1m-mvp`, close to users, about 500 MB free |
| 2 | Auth | **Supabase Auth**, with the backend verifying JWTs | Don't write password storage and reset flows ourselves. Free for about 50k monthly users, and users can be exported later |
| 3 | Login methods | **Google + email/password** | Free. Phone OTP is what Indian SMEs prefer, but SMS costs money per message, so it waits for revenue |
| 4 | Backend host | **Render free**, Docker, Singapore | No ops work and deploys from Git. It sleeps after 15 min idle (about 1 min to wake), which we address below. The container stays portable to Cloud Run or a $7 plan |
| 5 | Frontend host | **Cloudflare Pages** | Free, and generous on bandwidth. Vercel's Hobby plan disallows commercial use, so the README's advice needs changing |
| 6 | AI | **Gemini, behind per-tenant quotas** | See "The one thing that isn't free" below |
| 7 | PDF storage | **Postgres** (changed from Supabase Storage in Phase 1) | Commits in one transaction with the invoice, is covered by the nightly backup, and needs no extra secret. The cost is the smaller 500 MB limit, so move to object storage at about 400 MB |
| 8 | Tenancy model | **One user → one business** for now | Simplest correct option. Accountants with several clients become a later migration |
| 9 | Monitoring | **UptimeRobot + Sentry**, both free | See below |
| 10 | Backups | **GitHub Actions nightly `pg_dump`**, encrypted | The Supabase free plan appears to have no backups, and this data is financial records |
| 11 | Channels | **Telegram now, WhatsApp later** | Telegram's bot API is free. WhatsApp's Business API charges per conversation |

**One pinger solves three problems.** A 5-minute UptimeRobot check on `/ready` keeps Render awake (31 days × 24 h = 744 h, under the 750 h allowance), stops Supabase pausing after 7 idle days (this has already happened to `m1m-mvp`), and alerts us when we're down. The allowance is per workspace, so only production gets pinged. Staging is allowed to sleep.

### The one thing that isn't free

"Everything free" holds, with one exception I want to flag rather than bury: **the Gemini free tier isn't a good fit for real customer data.**

- **Privacy:** by most accounts Google's free-tier terms allow prompts to be used to improve its products. Those prompts would contain our customers' customers, prices and GSTINs.
- **Capacity:** reported limits vary from about 20 to 1,500 requests per day, are shared across all tenants, and have been cut without much notice.

**My recommendation:**
- **Pilot:** stay on the free tier, with informed consent from pilot businesses and quotas in place.
- **Before public launch:** turn on Gemini billing with a hard budget alert. Flash-class pricing should be a few hundred rupees a month at early volumes.
- **Fallback:** the rule-based parser keeps the core flows working when AI is unavailable.

The only other cost worth paying early is a domain (about ₹800 a year). Free subdomains work, but a business tool looks more trustworthy on its own domain.

### Scaling triggers: when free stops being enough

| Trigger | Move to | Cost |
|---|---|---|
| Database nears 400 MB, or first paying customers | Supabase Pro (daily backups, no pausing) | ~$25/mo |
| Cold starts or memory errors appear | Render Starter | ~$7/mo |
| Gemini quota hit regularly | Paid Gemini | Usage-based |

## Phases

### Phase 0: Foundations *(no accounts needed)* — built 2026-11-06, not yet committed
Make the code safe to deploy. Everything here is verifiable locally.

- Isolated test database, and CI
- Fail-closed config, production boot validation, CORS from config
- JWT verification, `/me`, business creation on signup
- Server-side onboarding state
- Authenticated PDF downloads
- Commit before responding
- Health and readiness checks, request IDs, safe error handling
- Login and signup UI, sign out, error boundary, editable business profile
- Production Dockerfile, `render.yaml`, untrack `m1m.db`

**Done when:** two businesses can sign up in tests, and neither can reach the other's data through any endpoint. **Met.** The login UI has only run against a local stand-in for Supabase Auth, so Phase 1 starts by proving it for real.

### Phase 1: Go live on staging *(needs account access)* — code done, deploy pending
**Done:**
- Supabase project restored, schema applied, every table locked against the public API
- Full test suite on real Postgres, plus a Postgres CI job; found and fixed a seed bug SQLite was hiding
- PDFs stored durably in Postgres, and failed documents fully rolled back
- Safe numbering, stock and quotation conversion under simultaneous requests
- Per-business AI limits and per-IP rate limits
- Backup workflow, Sentry support and deployment guide written

**What I need from you** (these need your accounts):
1. Sign up once on the local app with real login, to prove the Supabase Auth flow.
2. Commit this work and push it, so CI runs and builds the Docker image.
3. Create the Render and Cloudflare Pages services, following the [deployment guide](./DEPLOYMENT.md).
4. Add the two backup secrets in GitHub, run the backup once, and rehearse a restore.
5. Set up custom SMTP in Supabase and an UptimeRobot monitor.

**Done when:** a stranger can sign up on the staging URL and download a real invoice, and that PDF survives a restart.

### Phase 2: Closed pilot, 3–5 businesses *(about 2 weeks of real use)*
- Have a CA review invoices against GST Rule 46 and numbering rules
- Terms, Privacy Policy, consent at signup
- Payments recording, and customer and item CRUD screens
- Logo and bank/UPI details on documents
- Rehearse a backup restore, write the runbook

**Done when:** pilot businesses have issued real invoices for two weeks with no data incidents and a CA sign-off.

### Phase 3: Public launch
- Landing page, Row-Level Security, invoice immutability and credit notes
- Data export and account deletion, paid Gemini, accessibility pass, end-to-end smoke test in CI

**Done when:** every P0 and P1 item in the checklist is closed.

### Phase 4: After launch
Staff roles, audit log, pagination, Hindi UI, share links, then WhatsApp once revenue covers it.

## Top risks

| Risk | Impact | Mitigation |
|---|---|---|
| Cross-tenant data leak | Fatal to trust | Tenant from server only, isolation tests in CI, RLS before launch |
| Lost financial records | Severe, possibly a legal issue | Nightly backups, rehearsed restore, stored PDFs |
| Incorrect GST invoices | Customers face compliance trouble | CA review before pilot use; the deterministic calculator is already well tested |
| Free tier changes without notice | Outage or sudden cost | Portable container, standard Postgres, swappable storage |
| Gemini limit exhausted | Assistant degrades for everyone | Per-tenant quotas, rule-based fallback, paid tier at launch |
| Render's sleep breaks Telegram tasks | Lost messages | Keep-warm ping now, durable processing in P1 |
