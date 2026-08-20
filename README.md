# M1M | Munim.ai

> A business copilot for Indian small and medium-sized businesses.

M1M turns natural-language requests into operational results: quotations, GST-compliant invoices, PDF documents, and document history. The same agent workflow is designed to serve web and WhatsApp channels while keeping business rules and data access in one backend.

This repository is an incremental MVP containing the backend, database schema and migrations, deterministic seed data, LangGraph workflows, PDF generation, and a React developer UI.

## Contents

- [What M1M Does](#what-m1m-does)
- [How It Works](#how-it-works)
- [Repository Layout](#repository-layout)
- [Technology](#technology)
- [Requirements](#requirements)
- [Clone and Install](#clone-and-install)
- [Configure the Environment](#configure-the-environment)
- [Choose a Database](#choose-a-database)
- [Run Migrations and Seed Data](#run-migrations-and-seed-data)
- [Run the Application](#run-the-application)
- [API Endpoints](#api-endpoints)
- [Tests and Verification](#tests-and-verification)
- [Common Problems](#common-problems)
- [Project Scope and Limitations](#project-scope-and-limitations)

## What M1M Does

M1M is built around the daily workflow of an Indian SME owner:

1. The user writes a request in natural language, such as asking for a quotation or invoice.
2. The agent identifies the intent and resolves the customer and items from the database.
3. Deterministic business logic calculates taxable values and GST.
4. The application creates the business document and renders a PDF.
5. The web client displays the response and makes the generated document available for download.

The data model supports tenants, users, customers, items, HSN codes, GST rates, stock, quotations, invoices, payments, conversation logs, Tally connection placeholders, and external ID mappings.

For GST routing, Maharashtra customers can use CGST + SGST, while customers in another state can use IGST. GST calculation is deterministic and should not depend on an LLM response.

## How It Works

```mermaid
flowchart LR
		U[Business owner] --> W[React web UI]
		W --> A[FastAPI API]
		A --> G[LangGraph agent]
		G --> S[Customer and item lookup]
		G --> C[GST and document services]
		S --> D[(SQLite / PostgreSQL / Supabase)]
		C --> P[Generated PDF]
		A --> W
		P --> W
```

The backend is the source of truth. The frontend uses Vite's development proxy to forward `/api` and `/documents` requests to FastAPI.

## Repository Layout

```text
.
├── backend/
│   ├── app/
│   │   ├── agent/          LangGraph state and workflow
│   │   ├── api/v1/         Chat and document endpoints
│   │   ├── db/             Async SQLAlchemy session and Alembic migrations
│   │   ├── models/         Database models
│   │   └── services/       GST, lookup, numbering, Gemini, and PDF services
│   ├── scripts/seed.py     Idempotent fictional development data
│   ├── templates/          Invoice and quotation HTML templates
│   ├── requirements.txt    Python dependencies
│   └── alembic.ini         Migration configuration
├── frontend/
│   ├── src/                React + TypeScript application
│   ├── package.json        Node dependencies and scripts
│   └── vite.config.ts      Dev server and API proxy
├── generated_docs/         Generated quotation and invoice PDFs
├── m1m-mvp-prd.md          Product requirements
├── m1m-mvp-trd.md          Technical requirements
├── .env.example            Environment variable template
└── README.md               This guide
```

## Technology

| Area | Technology |
| --- | --- |
| Backend API | FastAPI, Uvicorn |
| Language | Python 3.11+ |
| Agent orchestration | LangGraph |
| ORM and database access | SQLAlchemy 2.x async |
| Database options | SQLite, local PostgreSQL 15+, or Supabase PostgreSQL |
| Migrations | Alembic |
| AI provider | Google Gemini API |
| PDF generation | Jinja2 + WeasyPrint |
| Frontend | React 19, TypeScript, Vite |
| Testing | pytest, pytest-asyncio |

## Requirements

Install these on a new PC:

- Git
- Python 3.11 or newer
- Node.js and npm (Node.js 20 LTS or newer is recommended)
- A code editor such as VS Code
- One database option: SQLite, local PostgreSQL 15+, or a Supabase PostgreSQL project
- A Gemini API key for Gemini-backed flows and the Gemini smoke test

SQLite is the fastest way to run the project because it requires no database server or Supabase account.

## Clone and Install

Open PowerShell:

```powershell
git clone <repository-url>
Set-Location m1m-business-workflow-agent

python --version
node --version
npm --version
```

Create and activate the Python virtual environment:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Install frontend dependencies:

```powershell
Set-Location frontend
npm install
Set-Location ..
```

Keep the virtual environment activated while running backend commands. Each new PowerShell window must activate it again.

## Configure the Environment

Copy the template in the repository root:

```powershell
Copy-Item .env.example .env
```

The root `.env` is automatically discovered by the backend, Alembic, and seed script. Never commit it because it can contain database credentials and API keys.

### Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `DB_ENVIRONMENT` | No | `sqlite`, `local_postgres`, or `supabase`; defaults to `sqlite` |
| `DATABASE_URL` | Supabase | PostgreSQL connection URL; also overrides `DB_ENVIRONMENT` when non-empty |
| `DB_HOST` | Local PostgreSQL | Database host, normally `localhost` |
| `DB_PORT` | Local PostgreSQL | Database port, normally `5432` |
| `DB_NAME` | Local PostgreSQL | Database name, normally `m1m_local` |
| `DB_USER` | Local PostgreSQL | Database user, normally `postgres` |
| `DB_PASSWORD` | Local PostgreSQL | Database password |
| `ENV` | No | `development` or `production`; development enables API docs and SQL echo |
| `SPRINT_TENANT_ID` | No | Tenant UUID used by the Sprint 1 UI and API; otherwise the seeded development UUID is used |
| `GEMINI_API_KEY` | Gemini flows | API key from Google AI Studio |

The backend accepts `postgresql://`, `postgres://`, and `postgresql+asyncpg://` URLs and normalizes PostgreSQL URLs for the async driver.

## Choose a Database

Choose exactly one profile in `.env`. After changing profiles, run migrations and seed data against the newly selected database.

### Option A: SQLite, no external database setup

```dotenv
DB_ENVIRONMENT=sqlite
DATABASE_URL=
```

The application creates or uses `m1m.db` in the repository root. No PostgreSQL installation or Supabase project is needed.

### Option B: Local PostgreSQL, without Supabase

Install PostgreSQL 15 or newer, create a database, and set:

```dotenv
DB_ENVIRONMENT=local_postgres
DATABASE_URL=
DB_HOST=localhost
DB_PORT=5432
DB_NAME=m1m_local
DB_USER=postgres
DB_PASSWORD=your_local_postgres_password
```

For example, create the database with `psql`:

```sql
CREATE DATABASE m1m_local;
```

Leave `DATABASE_URL` empty. A non-empty `DATABASE_URL` always takes priority over the local PostgreSQL settings.

### Option C: Supabase PostgreSQL

Create a Supabase project, open its database connection settings, and copy a PostgreSQL connection string into `.env`:

```dotenv
DB_ENVIRONMENT=supabase
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
```

Use the connection string supplied by Supabase. Keep the password private and URL-encode special characters when required. M1M enables the connection handling needed for Supabase PostgreSQL connections.

To switch away from Supabase, clear `DATABASE_URL` first and then select `DB_ENVIRONMENT=sqlite` or `DB_ENVIRONMENT=local_postgres`.

## Run Migrations and Seed Data

Run migrations from `backend`, because the Alembic script location is relative to that directory. Run the seed script from the repository root:

```powershell
Set-Location backend
alembic -c alembic.ini upgrade head
Set-Location ..
python backend\scripts\seed.py
```

Alembic is the only supported owner of the database schema. Do not use `create_all()` as a replacement for migrations.

The seed script is safe to run repeatedly. It inserts deterministic fictional development data:

- 1 tenant: Vaidya Industrial Supplies
- 8 customers: Maharashtra and inter-state examples
- 12 catalog items
- 12 opening stock records

Verify idempotency by running the seed twice:

```powershell
python backend\scripts\seed.py
python backend\scripts\seed.py
```

Useful migration commands:

```powershell
Set-Location backend
alembic -c alembic.ini current
alembic -c alembic.ini history
alembic -c alembic.ini downgrade -1
Set-Location ..
```

## Run the Application

Use two PowerShell windows.

### Terminal 1: backend

From the repository root:

```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- Health check: <http://127.0.0.1:8000/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

API documentation is enabled when `ENV=development`.

### Terminal 2: frontend

```powershell
Set-Location frontend
npm run dev
```

Open <http://localhost:5173>. Vite forwards `/api` and `/documents` to the backend at port 8000.

For a production-style frontend build:

```powershell
npm run build
npm run preview
```

The frontend preview server runs on port 4173 and is also allowed by the backend CORS configuration.

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend liveness check |
| `POST` | `/api/v1/chat` | Send a natural-language business request |
| `GET` | `/api/v1/documents` | List quotations and invoices for the active tenant |
| `GET` | `/documents/{tenant_id}/{doc_type}/{filename}` | Download a generated PDF |

Example chat request:

```powershell
Invoke-RestMethod `
	-Uri http://127.0.0.1:8000/api/v1/chat `
	-Method Post `
	-ContentType "application/json" `
	-Body '{"message":"Create a quotation for Ramesh Traders for 10 TMT Steel Rod 12mm"}'
```

The response can include the detected intent, document type, document number, structured data, and a PDF URL.

## Tests and Verification

Run backend tests from the backend directory:

```powershell
Set-Location backend
pytest tests -v
Set-Location ..
```

Database-dependent seed tests expect the schema and seed data to exist. Run migrations and seeding first.

The Gemini smoke test makes a real external API request. Set a valid `GEMINI_API_KEY` before running it, or skip it when working offline:

```powershell
pytest tests -v -k "not gemini"
```

Basic database checks are available from the repository root:

```powershell
python check_db.py
python check_seed_paths.py
```

## Common Problems

**The application connects to the wrong database**

Check `.env`. If `DATABASE_URL` is non-empty, it overrides `DB_ENVIRONMENT`. Clear it when using SQLite or local PostgreSQL component settings.

**Supabase connection fails**

Confirm that the URL is copied from the correct Supabase project, the password is correct, and the database is reachable. Then rerun the migration command from `backend`.

**The API starts but the UI cannot connect**

Start FastAPI on port 8000 and Vite on port 5173. The frontend proxy is configured for those ports.

**The chat request cannot find a tenant or customer**

Run migration and seed commands using the same `.env` profile as the API. Confirm that `SPRINT_TENANT_ID` is empty or matches the seeded tenant UUID.

**PDF generation fails on Windows**

WeasyPrint may require native runtime dependencies on some Windows installations. Install the runtime dependencies documented for the installed WeasyPrint version, then restart the virtual environment and retry.

## Project Scope and Limitations

The current MVP intentionally uses a single development tenant selected through `SPRINT_TENANT_ID`. Authentication, production multi-tenant isolation, and PostgreSQL row-level security are not implemented yet.

Planned follow-up areas include:

- Authentication with phone OTP and JWT sessions
- RLS policies and cross-tenant isolation tests
- Production onboarding and business configuration
- Dues and stock-query agents
- CSV import, OCR, voice notes, analytics, and deployment automation
- WhatsApp Cloud API integration
- Tally integration and payment workflows

Seed records are fictional development data only. Do not use them as real business or customer information.

## Security Notes

- Keep `.env` out of version control.
- Never place database passwords or Gemini keys in source code.
- Use `ENV=production` only with a proper deployment configuration and authentication layer.
- Treat the Sprint 1 tenant fallback and generated PDFs as development-only behavior.

## Product Documents

- [Product requirements](m1m-mvp-prd.md)
- [Technical requirements](m1m-mvp-trd.md)

---

M1M is built incrementally: start with SQLite for a zero-setup local run, move to local PostgreSQL when you need a real PostgreSQL environment, and use Supabase when you need managed PostgreSQL infrastructure.
