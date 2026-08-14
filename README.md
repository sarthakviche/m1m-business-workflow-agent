# M1M (Munim.ai) — WhatsApp + Web Business Copilot for Indian SMEs

## Quick Setup

### Prerequisites
- Python 3.11+
- Node 18+
- A Supabase project (see `docs/m1m-mvp-implementation-plan.md` Part A for setup)

### 1. Clone and configure environment

```bash
cp .env.example .env
# Fill in all values in .env — see docs/m1m-mvp-implementation-plan.md Part A.6
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies (WeasyPrint binary-only to avoid C build tools):
pip install weasyprint --only-binary :all:
pip install -r requirements.txt

# Run database migrations against Supabase:
alembic upgrade head

# Start dev server:
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Tests

```bash
cd backend
pytest tests/
```

## Architecture

See `docs/m1m-mvp-trd.md` for full technical spec.  
See `docs/m1m-mvp-prd.md` for product scope (four locked features).  
See `docs/m1m-mvp-implementation-plan.md` for build phase order.

## Free-tier services in use

| Service | Purpose |
|---------|---------|
| Supabase | Postgres DB + Storage (PDFs) |
| Google Gemini API | LLM intent parsing |
| Meta WhatsApp Cloud API | WhatsApp channel |
| Render | Backend hosting |
| Vercel | Frontend hosting |

**Total cost: ₹0/month for MVP pilot.** See implementation plan Part C for limits.
