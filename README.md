# URL Shortener API – LinkLy AI Backend

A **production-grade URL Shortener** with Gemini-powered LangGraph AI agents, click analytics, and a full agentic SDLC orchestration engine.

---

## Live Links

| Resource | URL |
|---|---|
| **Production API** | https://backend-six-pied-13.vercel.app |
| **Swagger UI** | https://backend-six-pied-13.vercel.app/docs |
| **Health Check** | https://backend-six-pied-13.vercel.app/health |
| **GitHub** | https://github.com/satyamjaysawal/URL-Shortener-API |
| **Frontend (LinkLy AI)** | https://frontend-dun-chi-79.vercel.app |
| **Frontend GitHub** | https://github.com/satyamjaysawal/url-shortener-frontend |

---

## Features

- **URL shortening** – Custom aliases, expiry, soft-delete
- **Click analytics** – Per-redirect events, daily breakdown, top referrers
- **AI URL analysis** – LangGraph workflow with Gemini (safety, category, tags, smart alias)
- **Streaming agent UI** – SSE endpoint for real-time LangGraph node events
- **User API keys** – Optional per-request `gemini_api_key` (session-based on frontend)
- **Reliability** – LRU cache, rate limiting, audit logging, health checks
- **SDLC orchestrator** – Requirements → Architecture → Implementation → Testing ‖ Documentation → Release

---

## Quick Start (Local)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create or edit `.env`:

```env
MONGODB_URI=mongodb+srv://...
DATABASE_NAME=url-shortener-project-db
BASE_URL=http://localhost:8000
GOOGLE_API_KEY=your-gemini-api-key
```

### 3. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

Visit:
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 4. Run the Frontend (optional)

```bash
cd ../frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## AI LangGraph Workflow

```
[Entry] → [Analyze URL] → [Governance Gate] → [Suggest Alias] → [Complete]
                              ↓ (unsafe)
                           [Blocked]
```

| Node | Description |
|---|---|
| `analyze_url` | Gemini safety scan, categorization, tag extraction |
| `governance_router` | Blocks unsafe URLs; routes to alias suggestion when safe |
| `suggest_alias` | AI-generated 4–6 char alias (skipped if custom alias provided) |

**Endpoints:**
- `POST /ai/analyze` – Full analysis (JSON response)
- `POST /ai/analyze/stream` – Server-Sent Events stream of node execution

---

## Run the Agentic Orchestrator

```bash
# Greenfield scenario (build from scratch)
python run_orchestrator.py --scenario greenfield

# Brownfield scenario (enhance existing code)
python run_orchestrator.py --scenario brownfield

# Ambiguous scenario (resolve vague requirements)
python run_orchestrator.py --scenario ambiguous

# Run all three scenarios
python run_orchestrator.py --scenario all

# With interactive human approval at release gate
python run_orchestrator.py --scenario greenfield --no-auto-approve
```

> **Windows note**: Run with `$env:PYTHONUTF8=1; python run_orchestrator.py --scenario all` to enable full Unicode output in the terminal.

**Outputs generated:**
- `audit.jsonl` – Full JSON-L audit trail
- `pipeline_state.json` – Serialized pipeline state with decision lineage
- `orchestrator.log` – Structured log file

---

## Run Tests

```bash
# All tests
pytest tests/ -v --tb=short

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

---

## Project Structure

```
backend/
├── app/                      # FastAPI application
│   ├── main.py               # App entrypoint + lifespan
│   ├── config.py             # Pydantic settings
│   ├── models/               # Pydantic data models (url, ai)
│   ├── routers/              # Route handlers (shorten, ai, analytics, health)
│   ├── services/             # Business logic + LangGraph agent
│   ├── db/                   # MongoDB connection
│   └── middleware/           # Rate limiting, audit logging
│
├── orchestrator/             # Agentic SDLC engine
│   ├── orchestrator.py       # Main DAG pipeline runner
│   ├── stages/               # 6 SDLC stage implementations
│   ├── graph.py              # Dependency DAG
│   ├── state.py              # Stateful cross-stage context
│   ├── governance.py         # Policy guardrails + approval
│   ├── metrics.py            # Reliability metrics
│   └── audit.py              # JSON-L audit logger
│
├── scenarios/                # Three demonstration scenarios
├── tests/                    # Test suite (unit + integration)
├── docs/                     # Documentation
├── run_orchestrator.py       # Orchestrator CLI
├── requirements.txt
├── vercel.json               # Vercel serverless config
└── .env
```

---

## API Endpoints Summary

| Method | Path | Description |
|---|---|---|
| POST | `/shorten` | Create short URL (with optional AI alias) |
| GET | `/{short_code}` | Redirect (302) |
| DELETE | `/api/urls/{short_code}` | Soft-delete |
| POST | `/ai/analyze` | AI URL analysis (JSON) |
| POST | `/ai/analyze/stream` | AI analysis (SSE stream) |
| GET | `/analytics/stats/{code}` | Basic stats |
| GET | `/analytics/detail/{code}` | Full analytics |
| GET | `/analytics/top` | Top URLs |
| GET | `/health` | Health check |
| GET | `/metrics` | Cache metrics |

---

## Architecture Highlights

- **FastAPI** – Async, typed, auto-docs
- **MongoDB** – Flexible schema, `clicks` collection for analytics
- **LangGraph + Gemini** – Agentic URL analysis and alias suggestion
- **LRU Cache** – In-memory hot-path cache (1000 entries, 5 min TTL)
- **Rate Limiting** – Sliding-window 30 req/min per IP
- **Audit Logging** – Every request logged with trace ID
- **Vercel** – Serverless Python deployment via `@vercel/python`

---

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Orchestration Model](docs/orchestration_model.md)
- [API Reference](docs/api_reference.md)
- [Trade-offs & Risks](docs/trade_offs.md)

---

## Deployment

Deployed on **Vercel** from the `main` branch:

```bash
cd backend
vercel --prod --yes
```

Production URL: https://backend-six-pied-13.vercel.app