# Travel Risk Alert Platform

Travel Risk Alert Platform is a full-stack system for aggregating travel risk signals, scoring them, and delivering operational alerts.

## Stack

- Frontend: Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui
- Backend: FastAPI, SQLAlchemy, Pydantic
- Data: PostgreSQL + PostGIS
- Cache/Queue: Redis + Celery

## Prerequisites

- Docker Desktop (recommended for local setup)
- Or local runtimes:
  - Python 3.11+
  - Node.js 20+
  - PostgreSQL 16+ with PostGIS
  - Redis 7+

## Environment Setup

1. Copy `.env.example` to `.env`.
2. Update secrets before non-local deployment:
   - `SECRET_KEY`
   - `JWT_SECRET_KEY`
   - API keys (`OPENAI_API_KEY`, `NEWSAPI_KEY`, etc.)
3. Optional Phase 8 controls:
   - `RATE_LIMIT_ENABLED`
   - `RATE_LIMIT_REQUESTS`
   - `RATE_LIMIT_WINDOW_SECONDS`
   - `RATE_LIMIT_EXEMPT_PATHS`

## Run with Docker Compose

From the project root:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

## Run Locally Without Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Testing

Backend tests (unittest):

```bash
cd backend
python -m unittest discover -s tests -p "test_*.py"
```

Frontend lint/type checks:

```bash
cd frontend
npm run lint
```

## Phase 8 Hardening

The project now includes:

- Centralized backend exception handlers with consistent API error payloads
- Configurable backend request rate limiting middleware
- Global frontend loading and error boundaries (`app/loading.tsx`, `app/error.tsx`)
- Admin system health panel with loading, retry, and failure states
- Backend middleware and handler test coverage

## Notes

- Rate limiting is in-memory and process-local by default; use a shared store for multi-instance production deployments.
- `/health` and `/health/db` are exempt from rate limiting by default.
