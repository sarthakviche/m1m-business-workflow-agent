# <p align="center"><img src="./docs/assets/banner.png" alt="Munim.ai Banner" width="700"/></p>

<p align="center">
  <strong>Autonomous AI Business Workflow & GST Operations Agent for Indian SMEs</strong>
</p>

<p align="center">
  <a href="#-key-features"><img src="https://img.shields.io/badge/Status-Sprint%201%20MVP%20Ready-brightgreen?style=for-the-badge" alt="Status"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/AI-LangGraph%20%7C%20Gemini%202.5-orange?style=for-the-badge" alt="AI Stack"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-blue?style=for-the-badge&logo=fastapi" alt="Backend"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Frontend-React%2019%20%7C%20Vite%20%7C%20Tailwind-61DAFB?style=for-the-badge&logo=react" alt="Frontend"></a>
  <a href="#-tests--quality-assurance"><img src="https://img.shields.io/badge/Tests-136%20Passed-success?style=for-the-badge" alt="Tests"></a>
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

# Tenant & Security
SPRINT_TENANT_ID=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
APP_SECRET_KEY=generate_a_random_32_character_secret_key
```

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

---

## 🧪 Tests & Quality Assurance

The codebase includes an extensive automated test suite covering unit math, database operations, fuzzy lookup scores, and full LangGraph workflow execution.

```bash
# Run all automated tests
pytest backend/tests -v

# Run fast offline tests (bypassing external LLM network calls)
pytest backend/tests -v -k "not gemini"
```

```text
======================= 136 passed in 12.45s =======================
```

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

- **Frontend (Vercel):** Connect repository, set Root Directory to `frontend`, and configure `vercel.json` rewrites to proxy `/api` and `/documents` to your backend.
- **Backend (Render / Railway / GCP Cloud Run):** Deploy Python 3.12 container with `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`.
- **Database (Neon / Supabase):** Connect serverless PostgreSQL via `DATABASE_URL=postgresql+asyncpg://...` and run `alembic upgrade head`.

*(For complete slide-ready technical documentation, see [`MVP-technical-working.md`](./MVP-technical-working.md)).*

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

<p align="center">
  <sub>Built with ❤️ for Indian Small & Medium Enterprises.</sub>
</p>
