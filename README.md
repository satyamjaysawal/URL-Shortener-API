# URL Shortener – Agentic SDLC System

A **production-grade URL Shortener** with a full agentic SDLC orchestration engine demonstrating the complete software lifecycle: Requirements → Architecture → Implementation → Testing → Documentation → Release.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd assignment
pip install -r requirements.txt
```

### 2. Configure Environment

`.env` is pre-configured with your MongoDB Atlas connection:
```env
MONGODB_URI=mongodb+srv://...
DATABASE_NAME=url-shortener-project-db
BASE_URL=http://localhost:8000
```

### 3. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

Visit:
- **Swagger UI**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

---

## 🤖 Run the Agentic Orchestrator

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

## 🧪 Run Tests

```bash
# All tests
pytest tests/ -v --tb=short

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

---

## 📁 Project Structure

```
assignment/
├── app/                      # FastAPI application
│   ├── main.py               # App entrypoint + lifespan
│   ├── config.py             # Pydantic settings
│   ├── models/               # Pydantic data models
│   ├── routers/              # Route handlers
│   ├── services/             # Business logic
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
│   ├── greenfield.py         # Build from scratch
│   ├── brownfield.py         # Enhance existing code
│   └── ambiguous.py          # Handle vague requirements
│
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration + E2E tests
│
├── docs/                     # Documentation
│   ├── architecture.md
│   ├── orchestration_model.md
│   ├── api_reference.md
│   └── trade_offs.md
│
├── run_orchestrator.py       # Orchestrator CLI
├── requirements.txt
└── .env
```

---

## 🔗 API Endpoints Summary

| Method | Path | Description |
|---|---|---|
| POST | `/shorten` | Create short URL |
| GET | `/{short_code}` | Redirect (302) |
| DELETE | `/api/urls/{short_code}` | Soft-delete |
| GET | `/analytics/stats/{code}` | Basic stats |
| GET | `/analytics/detail/{code}` | Full analytics |
| GET | `/analytics/top` | Top URLs |
| GET | `/health` | Health check |
| GET | `/metrics` | Cache metrics |

---

## 🏗️ Architecture Highlights

- **FastAPI** – Async, typed, auto-docs
- **MongoDB** – Flexible schema, `clicks` collection for analytics
- **LRU Cache** – In-memory hot-path cache (1000 entries, 5 min TTL)
- **Rate Limiting** – Sliding-window 30 req/min per IP
- **Audit Logging** – Every request logged with trace ID
- **Orchestrator** – Pure Python DAG: Requirements→Architecture→Implementation→(Testing‖Documentation)→Release

---

## 🛡️ Orchestration Features

| Feature | Implementation |
|---|---|
| DAG execution | Topological sort with parallel batches |
| State persistence | JSON file (`pipeline_state.json`) |
| Bounded retry | Max 3, exponential backoff [1s, 2s, 4s] |
| Rollback | Per-stage `rollback()` methods |
| Human approval | Release gate checkpoint |
| Governance | URL policy, entry gates, schema change control |
| Audit trail | JSON-L with run ID, stage, action, outcome |
| Metrics | Success rate, retry count, MTTR, E2E latency |

---

## 📖 See Also

- [Architecture Overview](docs/architecture.md)
- [Orchestration Model](docs/orchestration_model.md)
- [API Reference](docs/api_reference.md)
- [Trade-offs & Risks](docs/trade_offs.md)
