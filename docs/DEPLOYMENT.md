# Deploying Munim on free tiers

The target setup, and why it was chosen, is in [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md).

```
Browser ──► Vercel (web app, landing page)
   │
   ├──────► Supabase Auth (login)
   └──────► Render (API, Docker) ──► Supabase Postgres, Mumbai (data and PDFs)
                ▲
UptimeRobot ────┤ pings /ready every 5 min
Telegram ───────┘ webhook
GitHub Actions ──► nightly encrypted backup of Postgres
```

## Branches: what deploys from where

| Piece | Host | Deploys from | How |
|---|---|---|---|
| API (`munim-api-staging`) | Render | **`staging`** | Automatically on every push to `staging` |
| Web app (`munim-app`) | Vercel | **`main`** | Automatically on every push to `main`. Other branches and pull requests get preview URLs only |
| Landing page (`munim-landing`) | Vercel | Not linked to Git | By hand: `npx vercel deploy landing/site --prod` |
| Nightly database backup | GitHub Actions | **`main`** | Scheduled runs only start from the default branch |

`main` is protected: changes reach it only through a pull request. Keep `main` and `staging` on the same commit:

1. Push your work to `staging`. Render redeploys the API.
2. Open a pull request from `staging` into `main` and merge it once CI passes. Vercel redeploys the web app.
3. If the merge commit isn't on `staging` yet, fast-forward `staging` to `main` (`git push origin origin/main:staging`).

The API ships first, so a new endpoint is live before the web app that calls it. A database migration runs when the API container starts.

Live URLs: API `https://munim-api-staging.onrender.com`, web app `https://munim-app-two.vercel.app`, landing page `https://munim-landing.vercel.app`.

## 1. Supabase

The `m1m-mvp` project (`jstfqdoefjfqfwgppmxh`, Mumbai) is active, with the schema applied and every table locked down.

1. **Connect → Session pooler:** copy the connection string and fill in the database password. It's `DATABASE_URL`. Reset the password first if you don't have it.
2. **Authentication → URL Configuration:** set the Site URL to your web app URL, and add it to the redirect allow list.
3. **Authentication → Emails → SMTP:** add custom SMTP. The built-in sender only allows a few emails an hour, which blocks signups. Brevo's free tier is one option.
4. Optional: **Authentication → Providers → Google**, then set `VITE_AUTH_GOOGLE=true` on the web app.

Project URL: `https://jstfqdoefjfqfwgppmxh.supabase.co`. Publishable key: `sb_publishable_NqbVkTgtDNtsfop0t2hoSA_4ft8SE6U`. Both are public by design.

## 2. API on Render

1. **New → Blueprint**, pick this repository. It reads [`render.yaml`](../render.yaml), which deploys from `staging`.
2. Fill in the secrets when prompted:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Session pooler string from Supabase |
| `SUPABASE_URL` | `https://jstfqdoefjfqfwgppmxh.supabase.co` |
| `CORS_ORIGINS` | Your web app's `https://` origin (use a placeholder until step 3) |
| `GEMINI_API_KEY` | From Google AI Studio |
| `TELEGRAM_BOT_TOKEN` | From @BotFather (optional) |
| `TELEGRAM_WEBHOOK_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` (required if there's a bot token) |
| `SENTRY_DSN` | From a free Sentry project (optional) |

Migrations run at container start. **The app refuses to start if the config is unsafe**, and the log says which setting is the problem.

## 3. Web app on Vercel

**Add New → Project**, import this repository. [`frontend/vercel.json`](../frontend/vercel.json) sets the build, the single-page-app rewrite and the security headers. The landing page is a second Vercel project with root directory `landing/site` and no build step.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Production branch | `main` |
| `VITE_API_BASE_URL` | Your Render URL |
| `VITE_SUPABASE_URL` | `https://jstfqdoefjfqfwgppmxh.supabase.co` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | The publishable key above, **never** the secret key |

Then put this origin in Render's `CORS_ORIGINS`, and in Supabase's redirect list.

## 4. Telegram webhook

```bash
python backend/scripts/telegram_bot.py set-webhook https://<your-render-url>
```

## 5. Monitoring

**UptimeRobot:** HTTP monitor on `https://<your-render-url>/ready`, every 5 minutes, with email alerts. This keeps the free instance awake, stops Supabase pausing the project, and tells you when the app is down.

## 6. Backups

In GitHub → Settings → Secrets and variables → Actions, add:

| Secret | Value |
|---|---|
| `BACKUP_DATABASE_URL` | Session pooler string from Supabase |
| `BACKUP_PASSPHRASE` | A long random passphrase. **Keep a copy outside GitHub, or the backups can't be restored** |

[The workflow](../.github/workflows/backup.yml) runs nightly from `main`, and from the Actions tab on demand. Backups are kept 30 days. **Run it once and rehearse a restore before real customer data goes in:**

```bash
gpg --decrypt munim.dump.gpg > munim.dump
pg_restore --no-owner --dbname "<a scratch database URL>" munim.dump
```

GitHub turns off scheduled workflows after 60 days without repository activity, and emails you when it does.

## Checking a deploy

- `GET /health` and `GET /ready` both return `{"status": "ok", ...}`.
- `GET /api/v1/customers` with no credentials returns **401**. If it returns data, take the service down: `ENV` is wrong.
- Sign up as a new user, create a business, and create an invoice. Open the PDF.
- Redeploy from the Render dashboard, then open the PDF again. It must survive the restart.
- Sign up as a second user and confirm you can't see the first user's data.

## When the database fills up

PDFs live in Postgres, so the 500 MB free limit covers them too. Check it monthly:

```sql
select pg_size_pretty(pg_database_size(current_database()));
select pg_size_pretty(sum(length(content))), count(*) from document_file;
```

At about 400 MB, either move to Supabase Pro or move `document_file` contents to object storage. `pdf_service.load_pdf` and `_store_pdf` are the only code that would change.
