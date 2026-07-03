# Architecture Overview – URL Shortener System

## System Purpose

A production-grade URL Shortener service with:
- Core CRUD APIs (shorten, redirect, delete)
- **Gemini + LangGraph AI** for URL safety analysis and smart alias suggestion
- Click analytics (per-redirect event recording + aggregation)
- Reliability features (rate limiting, caching, health checks)
- A full agentic SDLC orchestration engine
- **LinkLy AI** React frontend with streaming agent visualization

---

## Live Deployment

| Component | URL |
|---|---|
| Frontend | https://frontend-dun-chi-79.vercel.app |
| Backend API | https://backend-six-pied-13.vercel.app |
| API Docs | https://backend-six-pied-13.vercel.app/docs |

---

## Component Map

```
┌─────────────────────────────────────────────────────────────┐
│              LinkLy AI Frontend (React + Vite)               │
│   Home │ Analytics │ Dashboard │ Orchestrator │ Theme Toggle │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS (VITE_API_BASE_URL)
          ┌────────────────▼────────────────┐
          │         FastAPI App              │
          │      (main.py + routers/)        │
          └────────────────┬────────────────┘
               Middleware Stack
          ┌────────────────┴────────────────┐
          │  AuditLogMiddleware              │  ← Trace ID on every request
          │  RateLimitMiddleware             │  ← 30 req/min per IP
          │  CORSMiddleware                  │
          └────────────────┬────────────────┘
          ┌────────────────▼────────────────┐
          │           Routers              │
          │  POST /shorten                 │
          │  POST /ai/analyze              │
          │  POST /ai/analyze/stream (SSE)   │
          │  GET  /{code}                    │
          │  DELETE /api/urls/{code}         │
          │  GET  /analytics/*               │
          │  GET  /health, /metrics          │
          └────┬──────────┬─────────┬───────┘
               │          │         │
    ┌──────────▼──┐  ┌────▼────┐  ┌─▼──────────────────┐
    │ URL Service  │  │Analytics│  │ Agent Service       │
    │ (url_service)│  │ Service │  │ (LangGraph + Gemini)│
    └──────┬───┬──┘  └────┬────┘  └─────────────────────┘
           │   │          │
    ┌──────▼─┐ │     ┌───▼────────┐
    │ Cache  │ │     │ MongoDB     │
    │ (LRU)  │ └────►│ urls coll  │
    └────────┘       │ clicks coll│
                     └────────────┘
```

---

## AI Agent Layer (LangGraph)

The `agent_service.py` module compiles a LangGraph `StateGraph`:

```
analyze_url → governance_router → suggest_alias → END
                    ↓ (unsafe)
                   END (blocked)
```

| Node | Role |
|---|---|
| `analyze_url` | Calls Gemini with structured JSON schema for category, safety, tags |
| `governance_router` | Conditional edge — blocks unsafe URLs, routes safe URLs to alias agent |
| `suggest_alias` | Generates 4–6 char alphanumeric alias (skipped if custom alias set) |

**API key resolution:** Per-request `gemini_api_key` from the frontend session takes priority over server `.env` `GOOGLE_API_KEY`.

**Streaming:** `stream_url_agent_workflow()` uses `agent_graph.astream(stream_mode="updates")` and emits SSE events for the frontend `AgentFlowGraph` component.

---

## Component Responsibilities

| Component | File | Responsibility |
|---|---|---|
| FastAPI App | `app/main.py` | Startup, middleware, routing |
| Config | `app/config.py` | Type-safe env settings |
| URL Service | `app/services/url_service.py` | Code generation, expiry, soft-delete, AI integration |
| Agent Service | `app/services/agent_service.py` | LangGraph workflow, Gemini calls, SSE streaming |
| Analytics Service | `app/services/analytics_service.py` | Click recording, aggregation |
| Cache Service | `app/services/cache_service.py` | LRU hot-path cache |
| MongoDB Layer | `app/db/mongodb.py` | Async connection with retry |
| Rate Limit MW | `app/middleware/rate_limit.py` | Sliding-window 30 req/min |
| Audit Log MW | `app/middleware/audit_log.py` | JSON logging with trace IDs |
| AI Router | `app/routers/ai.py` | `/ai/analyze` and `/ai/analyze/stream` |
| Orchestrator | `orchestrator/orchestrator.py` | SDLC DAG pipeline engine |

---

## Technology Choices

| Concern | Technology | Rationale |
|---|---|---|
| Web Framework | FastAPI | Async, typed, OpenAPI auto-docs |
| AI Orchestration | LangGraph | Stateful agent workflow with conditional routing |
| LLM | Google Gemini 2.5 Flash | Structured JSON output, fast inference |
| Database | MongoDB (motor) | Flexible schema, horizontal scale |
| ORM/Validation | Pydantic v2 | Type-safe, fast |
| Cache | In-memory LRU | Zero infra dependency |
| Frontend | React + Vite | SPA with SSE streaming support |
| Deployment | Vercel | Serverless backend + static frontend |
| Testing | pytest + httpx | Async-compatible |

---

## Data Flow: AI URL Analysis (Streaming)

```
Frontend → POST /ai/analyze/stream { long_url, gemini_api_key? }
  → AI Router
    → stream_url_agent_workflow()
      → analyze_url node (Gemini safety + category)
      → governance_router (unsafe → block, safe → continue)
      → suggest_alias node (if no custom alias)
      → SSE events: node_start, node_complete, workflow_complete
  → AgentFlowGraph updates UI in real time
```

## Data Flow: URL Shortening

```
Client → POST /shorten { long_url, custom_alias?, gemini_api_key? }
  → RateLimitMiddleware (check IP quota)
  → ShortenRouter
    → url_service.create_short_url()
      → Optional: run_url_agent_workflow() for smart alias
      → Check custom alias collision in MongoDB
      → Insert document into urls collection
  → 201 Created
```

## Data Flow: Redirect

```
Client → GET /{short_code}
  → RedirectRouter
    → url_service.resolve_url()
      → Cache HIT? → return long_url directly
      → Cache MISS → query MongoDB → cache result
    → analytics_service.record_click()
  → 302 Redirect to long_url
```

---

## Key Architectural Decisions

1. **LangGraph for AI routing**: Governance gate as conditional edge keeps safety logic declarative and streamable.
2. **Per-request API keys**: Users can bring their own Gemini key without server-side persistence.
3. **Separate `clicks` collection**: Avoids document bloat on hot URLs.
4. **LRU cache first**: Most redirects avoid DB for hot URLs. Cache TTL = 5 min.
5. **Soft-delete (`is_active`)**: Records retained for audit.
6. **SPA on Vercel**: Frontend `vercel.json` rewrites all paths to `index.html`.
7. **Async throughout**: Motor + FastAPI = non-blocking I/O under load.