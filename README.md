# <p align="center"><img src="./docs/assets/banner.png" alt="Munim.ai Banner" width="700"/></p>

<p align="center">
  <strong>Autonomous AI Business Workflow & GST Operations Agent for Indian SMEs</strong>
</p>

<p align="center">
  <a href="#-key-features"><img src="https://img.shields.io/badge/Status-Sprint%201%20MVP%20Ready-brightgreen?style=for-the-badge" alt="Status"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/AI-LangGraph%20%7C%20Gemini%202.5-orange?style=for-the-badge" alt="AI Stack"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-blue?style=for-the-badge&logo=fastapi" alt="Backend"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Frontend-React%2019%20%7C%20Vite%20%7C%20Tailwind-61DAFB?style=for-the-badge&logo=react" alt="Frontend"></a>
  <a href="#-tests--quality-assurance"><img src="https://img.shields.io/badge/Tests-320%20Passed-success?style=for-the-badge" alt="Tests"></a>
</p>

---

## 📌 Executive Summary

**M1M (Munim.ai)** is an AI-powered business copilot tailored specifically for Indian Small and Medium Enterprises (SMEs). It bridges the gap between chaotic, conversational commerce (WhatsApp, chat inquiries) and rigorous, audit-compliant ERP operations. 

Business owners and sales executives can interact in plain English or Hinglish to generate GST-compliant **Quotations**, convert estimates into **Tax Invoices**, check **Live Inventory & Pricing**, and dispatch branded **PDFs** in seconds—all backed by 100% deterministic tax computation and atomic ledger safeguards.

<p align="center">
  <img src="./docs/assets/value-prop.png" alt="Munim.ai Value Proposition" width="900"/>
</p>

---

## 🏛️ System Architecture

M1M pairs high-speed LLM entity extraction with deterministic business logic and relational database integrity.

<p align="center">
  <img src="./docs/assets/architecture.jpg" alt="Munim.ai System Architecture" width="950"/>
</p>

### 🔄 Agent Workflow (LangGraph)

```mermaid
graph TD
    User([User Prompt / WhatsApp Message]) --> API["FastAPI /api/v1/chat"]
    API --> Graph["LangGraph StateGraph"]
    Graph --> Classify["Node: classify_intent (Gemini 2.5 + Regex Fallback)"]
    
    Classify --> Route{"Conditional Edge: route_by_intent"}
    
    Route -->|"quotation"| QuoteAgent["Node: quotation_agent"]
    Route -->|"invoice"| InvoiceAgent["Node: invoice_agent"]
    Route -->|"catalog_query"| CatalogAgent["Node: catalog_agent"]
    Route -->|"clarify"| ClarifyAgent["Node: clarify_agent"]
    Route -->|"future_feature / off_topic"| OutOfScope["Node: out_of_scope_agent"]
    
    QuoteAgent --> LogNode["Node: log_conversation"]
    InvoiceAgent --> LogNode
    CatalogAgent --> LogNode
    ClarifyAgent --> LogNode
    OutOfScope --> LogNode
    
    LogNode --> Out([Structured Response + Downloadable PDF URL])
```

---

## ⚡ Key Features

- 💬 **Natural Language Business Documents:** Create quotations and invoices from conversational prompts (e.g., *"create quotation for Ramesh Traders for 200 units Steel Rod 12mm"*).
- 🧮 **Deterministic GST Calculator (Zero LLM Math):** Computes CGST, SGST, and IGST based on supplier and customer state codes using exact Python `Decimal` arithmetic.
- 🎯 **3-Tier Scored Fuzzy Customer Match:**
  - $\ge 0.80$: Silent auto-match.
  - $0.40 - 0.80$: Interactive confirmation pause (*"Did you mean Ramesh Enterprises? Or is this a new customer?"*).
  - $< 0.40$: Auto-creates new customer record with an explicit notification.
- 🔄 **1-Click Quotation-to-Invoice Conversion:** Convert `Q-YYYYMM-XXX` into `INV-YYYYMM-XXX` while decrementing stock atomically.
- 📦 **Fail-Safe Stock Validation:** Real-time inventory check blocks invoices when requested quantity exceeds warehouse stock.
- 🔍 **Live Catalog & Price Lookup:** Inquire about product pricing, HSN codes, and warehouse stock levels via chat without triggering document generation.
- 📷 **Price-List Onboarding:** Photograph a paper rate list (or upload a PDF/CSV) and Gemini transcribes items, prices, units, HSN and GST. Every row is validated and shown for review; nothing is saved until the owner confirms.
- 📑 **Audit-Grade PDF Generation:** Generates branded, GST-compliant PDFs using WeasyPrint with pure HTML/CSS fallbacks.

---

## 🛠️ Tech Stack

### AI & Agent Orchestration
- **LangGraph:** Stateful multi-agent graph orchestration and conditional routing.
- **Google Gemini 2.5 Flash / Pro:** High-speed intent classification and unstructured entity extraction.
- **Deterministic Regex Fallback:** Rule-based parser guaranteeing offline operational resilience.

### Backend & API
- **FastAPI:** High-performance asynchronous Python REST API framework.
- **Python 3.12:** Type-annotated async core runtime.
- **Pydantic v2:** Strict input validation and serialization models.
- **WeasyPrint / Cairo / Pango:** CSS Paged Media PDF generation engine.

### Database & Storage
- **PostgreSQL / SQLite:** Relational storage with multi-tenant isolation.
- **SQLAlchemy 2.0 (Async):** Modern asynchronous ORM with connection pooling.
- **Alembic:** Database schema migration management.

### Frontend
- **React 19 & Vite 8:** Lightning-fast single-page interface with hot module reloading.
- **TypeScript:** Fully typed API contracts and UI states.
- **Tailwind CSS:** Modern, responsive enterprise interface design.
- **Lucide Icons:** Clean UI iconography.

---

## 🚀 Getting Started

### 📋 Prerequisites

Ensure you have the following installed on your system:
- **Python:** `3.11` or `3.12` ([Download](https://www.python.org/downloads/))
- **Node.js:** `18.x` or `20.x` LTS ([Download](https://nodejs.org/))
- **Git:** ([Download](https://git-scm.com/))
- **Google Gemini API Key:** ([Get Key](https://aistudio.google.com/app/apikey))

---

### 📥 1. Clone the Repository

```bash
git clone https://github.com/your-username/m1m-business-workflow-agent.git
cd m1m-business-workflow-agent
```

---

### 🐍 2. Backend Setup

#### A. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### B. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

#### C. Configure Environment Variables

Create a `.env` file in the project root:

```ini
# Environment Mode: development | production
ENV=development

# Database Configuration (SQLite default for quick local run, or PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///./m1m.db
# For PostgreSQL: postgresql+asyncpg://postgres:postgres@localhost:5432/m1m_db

# Gemini AI API Key
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Demo tenant used when no one is logged in (development only)
SPRINT_TENANT_ID=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
```

With `ENV=development` there is no login, and everything runs as the seeded demo business. Any other value, including leaving `ENV` unset, requires login and refuses to start without safe production settings. See [`.env.example`](./.env.example) and [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

#### D. Run Database Migrations & Seed Data

```bash
# Apply schema migrations
alembic upgrade head

# Seed demo tenant profile, customers, and catalog items
python -m backend.app.db.seed
```

---

### 💻 3. Frontend Setup

In a new terminal window:

```bash
cd frontend
npm install
```

---

### 🏃 4. Running the Application

#### Start the Backend Server
```powershell
# From project root:
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```
Backend API will be live at: **`http://127.0.0.1:8000`**  
Interactive Swagger Docs: **`http://127.0.0.1:8000/docs`**

#### Start the Frontend Client
```bash
# In frontend directory:
npm run dev
```
Frontend Web UI will be live at: **`http://localhost:5173`**

### 🤖 5. Telegram Bot

The bot runs the same orchestrator as web chat. Each Telegram chat must be linked to a business with a one-time code before it can create documents.

1. Create a bot with [@BotFather](https://t.me/BotFather) and set `TELEGRAM_BOT_TOKEN` in `.env`.
2. Apply migrations: `cd backend && ..\.venv\Scripts\alembic.exe upgrade head`
3. Issue a link code, then send `/link CODE` to your bot:
   ```powershell
   .venv\Scripts\python.exe backend\scripts\telegram_bot.py link-code
   ```
4. **Local development** (no public URL needed): long-poll Telegram:
   ```powershell
   .venv\Scripts\python.exe backend\scripts\telegram_bot.py poll
   ```
5. **Production**: set `TELEGRAM_WEBHOOK_SECRET`, deploy the API behind HTTPS, then register the webhook:
   ```powershell
   .venv\Scripts\python.exe backend\scripts\telegram_bot.py set-webhook https://api.your-domain.com
   ```
   Telegram then calls `POST /api/v1/telegram/webhook`; requests without the matching secret header are rejected. Link codes can also be issued over HTTP with `POST /api/v1/telegram/link-codes` (authenticated by `X-API-Key`).

Bot commands: `/quotations`, `/invoices`, `/pdf NUMBER`, `/cancel`, `/unlink`, `/help`. Document lists and PDFs are read straight from the database. Free text goes to the agent, and its replies come from the catalog and tool results.

Send the bot a **photo, PDF or CSV of a price list** to import it. The bot reads it with the same checks as the web importer and lists what it found. If rows have no GST rate, it asks for one with buttons. It saves only when you tap **Save**. Rows without a price are skipped, and imports expire after 30 minutes.

### 📷 6. Price-List Import (onboarding)

New businesses add their catalog from **Stock → Import price list** (also offered at the end of first-run setup).

1. `POST /api/v1/catalog/import/preview` takes a photo (JPG/PNG/WEBP/HEIC), PDF or CSV up to 10 MB and returns rows to review. Nothing is written.
   - CSVs with recognisable headers (`Item`, `Rate`, `GST %`, `HSN`, `UOM`, `Stock`…) are parsed directly, with no model call.
   - Everything else goes to Gemini, which is told to leave unreadable or missing values empty rather than guess.
   - Prices ≤ 0, rates that aren't GST slabs and malformed HSN codes are dropped and flagged. Rows are matched to existing items by exact normalised name, so "TMT Rod 10mm" never overwrites "TMT Rod 12mm".
2. `POST /api/v1/catalog/import` saves the reviewed rows in one transaction. It creates new items, updates price/unit/GST/HSN on existing ones, and sets stock only where a quantity was given. Re-importing the same list changes nothing.

`PATCH /api/v1/business` updates the business name, state, GSTIN and address shown on documents.

---

## 🧪 Tests & Quality Assurance

The test suite covers GST maths, database operations, fuzzy lookups, LangGraph workflows, and multi-tenant isolation. Tests run offline against a throwaway database built from the real migrations, so they need no secrets and never touch your `m1m.db`.

```bash
cd backend

# Run all tests
pytest tests -q

# Also run the live Gemini smoke test (uses your real key and quota)
RUN_LIVE_GEMINI=1 pytest tests -q

# Run on a disposable Postgres, which adds the concurrency tests. Its data may be overwritten.
TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/postgres pytest tests -q
```

`tests/test_multi_tenant.py` is the security gate: two businesses sign up with real signed tokens and try to reach each other's data, and any new endpoint that doesn't require credentials fails the suite.

---

## 📖 Example Interactions

| User Prompt | System Action | Output Result |
| :--- | :--- | :--- |
| *"Create quotation for Ramesh Traders for 200 units Steel Rod 12mm"* | Extracts entity, matches customer, computes intra-state GST (CGST+SGST 18%), saves record. | Returns quotation summary + `Q-202608-001` PDF link. |
| *"Convert quotation Q-202608-001 into an invoice"* | Looks up quotation, verifies stock availability, marks quotation converted, decrements ledger. | Returns tax invoice `INV-202608-001` + download link. |
| *"What is the price and stock of PVC Pipe?"* | Queries `items` table without mutating draft states. | Returns unit price, HSN, tax rate, and warehouse stock. |
| *"Remind my customers about pending dues"* | Detects roadmap feature. | Delivers polite future-feature roadmap notice. |

---

## 📂 Project Directory Structure

```text
m1m-business-workflow-agent/
├── backend/
│   ├── app/
│   │   ├── agent/             # LangGraph state graph, nodes, and router
│   │   ├── api/v1/            # FastAPI REST endpoints (/chat, /documents, /health)
│   │   ├── core/              # Gemini client factory, logging, exceptions
│   │   ├── db/                # DB session management, seed script, migrations
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── services/          # GST calc, customer lookup, invoices, catalog, PDF
│   │   ├── templates/         # Clean HTML templates for WeasyPrint PDF generation
│   │   ├── config.py          # Pydantic Settings & environment manager
│   │   └── main.py            # FastAPI application factory
│   ├── tests/                 # 136 comprehensive pytest test suites
│   └── requirements.txt       # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/               # Typed fetch clients
│   │   ├── components/        # Chat messages, document drawers, UI components
│   │   ├── hooks/             # Custom React hooks (useChat)
│   │   ├── types/             # TypeScript data interfaces
│   │   ├── App.tsx            # Main application root
│   │   └── main.tsx           # React entry point
│   ├── package.json           # Frontend dependencies
│   ├── tailwind.config.js     # Tailwind CSS design system
│   └── vite.config.ts         # Vite proxy configuration
├── docs/
│   └── assets/                # Visual assets, banners, and architecture diagrams
├── MVP-technical-working.md   # In-depth slide-by-slide technical pitch deck guide
└── README.md                  # Project overview & documentation
```

---

## 🚢 Deployment Guide

Munim is designed to run on free tiers: Cloudflare Pages (web app), Render (API) and Supabase (database, auth, storage).

- [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md): step-by-step setup
- [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md): architecture decisions and roadmap
- [`docs/PRODUCTION_CHECKLIST.md`](./docs/PRODUCTION_CHECKLIST.md): what's done and what's left

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

<p align="center">
  <sub>Built with ❤️ for Indian Small & Medium Enterprises.</sub>
</p>
