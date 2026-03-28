# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ODGG is a conversational AI-guided dimensional modeling notebook. Users connect a database, walk through an 8-step Kimball methodology with AI assistance, and generate DDL, ETL SQL, and dbt models. The benchmark product is Cube.dev — ODGG differentiates via AI-first modeling.

## Commands

### Backend (Python/FastAPI)

```bash
cd backend
source .venv/bin/activate

# Install
uv pip install -e ".[dev]"

# Run dev server
uvicorn odgg.app:app --reload --port 8001

# Tests (all)
pytest

# Single test file
pytest tests/test_modeling_engine.py

# Single test
pytest tests/test_modeling_engine.py::test_suggest_grain -v

# Lint
ruff check odgg/ tests/
ruff format --check odgg/ tests/

# Auto-fix lint
ruff check --fix odgg/ tests/
ruff format odgg/ tests/
```

### Frontend (React/Vite)

```bash
cd frontend
pnpm install
pnpm dev          # Dev server on :3001, proxies /api → :8001
pnpm build        # TypeScript check + Vite production build
pnpm lint         # ESLint
```

### Docker (full stack)

```bash
docker compose up --build          # Everything: PostgreSQL + backend + frontend
docker compose up db               # Just the TPC-H sample database
```

### Sample Database Connection

- Host: `localhost`, Port: `5435`, DB: `tpch`, User: `odgg`, Pass: `odgg_dev`
- In Docker: Host: `db`, Port: `5432` (internal network)

## Architecture

Two-service architecture with a reverse proxy pattern:

- **Backend** (`backend/odgg/`): FastAPI app. All routes under `/api/v1/`. SQLite for session persistence, async PostgreSQL (asyncpg) for user database connections.
- **Frontend** (`frontend/src/`): React 19 + Vite. Both Vite dev proxy and nginx (Docker) forward `/api` → backend:8001.

### Backend Layers

- `app.py` — FastAPI entry point, mounts routers
- `api/v1/` — Route handlers: `sessions.py` (CRUD + step confirmation), `metadata.py` (schema discovery), `modeling.py` (AI suggestions + code generation)
- `services/` — Business logic:
  - `modeling_engine.py` — Kimball 4-step AI-guided modeling, builds metadata context for LLM prompts
  - `llm_router.py` — LiteLLM wrapper with two-schema retry strategy and SSE streaming. Handles code fence extraction and model-specific quirks (e.g. Kimi models skip temperature)
  - `metadata_discovery.py` — Async schema introspection via SQLAlchemy
  - `codegen.py` — Jinja2-based code generation (DDL, ETL, dbt)
  - `sanitizer.py` — Input sanitization and prompt injection detection
- `models/` — Pydantic models: `dimensional.py` (star schema types), `metadata.py` (schema snapshot), `session.py` (session + step state)
- `core/` — Config (`pydantic-settings`, env prefix `ODGG_`), database setup, logging
- `templates/` — Jinja2 templates for DDL, ETL, dbt, data dictionary

### Frontend Layers

- State: Zustand stores (`sessionStore`, `chatStore`, `datasourceStore`)
- Data fetching: TanStack React Query
- Diagram: React Flow (`@xyflow/react`) for star schema visualization
- Components: `StepNavigator` (8-step flow), `NotebookCell` (step content), `ModelDiagram` (React Flow), `ConnectStep` (DB connection form), `CodeOutput` (generated code display), `chat/` (AI conversation UI)

### Key Patterns

- All env vars use `ODGG_` prefix (see `core/config.py`)
- LLM calls go through `services/llm_router.py` → LiteLLM — never call LLM APIs directly
- Tests use `httpx.AsyncClient` with `ASGITransport` (no real server needed), `asyncio_mode = "auto"`
- The modeling engine sanitizes all database metadata before including it in LLM prompts (`sanitizer.py`)

## Conventions

- Backend: Python 3.11+, ruff for linting/formatting, line length 100
- Frontend: TypeScript strict, ESLint, pnpm
- Respond to users in Chinese, write code comments in English
- Commit after each meaningful change
