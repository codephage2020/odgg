# ODGG — 对话式数据维度建模 Notebook

Conversational AI-guided dimensional modeling. Connect your database, walk through Kimball's 4-step methodology with AI assistance, and generate DDL, ETL SQL, and dbt models.

## Quick Start

### Docker Compose (recommended)

```bash
# Start everything: PostgreSQL (TPC-H sample) + backend + frontend
docker compose up

# Open http://localhost:3001
```

### Local Development

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn odgg.app:app --reload --port 8001
```

**Frontend:**

```bash
cd frontend
pnpm install
pnpm dev
```

**Sample database:**

```bash
docker compose up db  # Start just the TPC-H PostgreSQL
# Connect via: postgresql://odgg:odgg_dev@localhost:5435/tpch
```

### CLI

```bash
uv pip install -e "./backend"

odgg connect --url "postgresql+asyncpg://odgg:odgg_dev@localhost:5435/tpch"
odgg generate --model model.json --output ./output
```

## Architecture

```
Frontend (React + Vite)        Backend (FastAPI)
┌──────────────────┐          ┌──────────────────────┐
│ StepNavigator    │  REST/   │ SessionMgr (SQLite)  │
│ NotebookCells    │◄──SSE──►│ ModelingEngine       │
│ ModelDiagram     │          │ MetadataDiscovery    │
│ (React Flow)     │          │ CodeGenEngine (Jinja2)│
└──────────────────┘          │ LLMRouter (LiteLLM)  │
                              │ InputSanitizer       │
                              └──────────────────────┘
```

## 8-Step Flow

| Step | Name | AI Role |
|------|------|---------|
| 1 | Connect Data Source | Provide templates |
| 2 | Metadata Discovery | Auto-scan tables/columns/relations |
| 3 | Select Business Process | Recommend based on schema |
| 4 | Define Grain | Analyze data, suggest grain |
| 5 | Select Dimensions | Identify candidates |
| 6 | Define Measures | Identify numeric columns |
| 7 | Generate Model | Star schema + validation |
| 8 | Generate Code | DDL + ETL + dbt |

## LLM Configuration

Set via environment variables:

```bash
ODGG_LLM_PROVIDER=openai    # openai | ollama | anthropic
ODGG_LLM_MODEL=gpt-4o
ODGG_LLM_API_KEY=sk-...
ODGG_LLM_BASE_URL=          # For Ollama: http://localhost:11434
```

### Zero-cost local setup (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.1

# Configure ODGG
export ODGG_LLM_PROVIDER=ollama
export ODGG_LLM_MODEL=llama3.1
export ODGG_LLM_BASE_URL=http://localhost:11434
```

## License

Apache 2.0
