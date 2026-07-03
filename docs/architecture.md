# Architecture Overview – URL Shortener System

## System Purpose

A production-grade URL Shortener service with:
- Core CRUD APIs (shorten, redirect, delete)
- Click analytics (per-redirect event recording + aggregation)
- Reliability features (rate limiting, caching, health checks)
- A full agentic SDLC orchestration engine

---

## Component Map

```
┌─────────────────────────────────────────────────────┐
│                   HTTP Client                        │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │     FastAPI App          │
          │  (main.py + routers/)   │
          └────────────┬────────────┘
               Middleware Stack
          ┌────────────┴────────────┐
          │  AuditLogMiddleware      │  ← Trace ID on every request
          │  RateLimitMiddleware     │  ← 30 req/min per IP
          │  CORSMiddleware          │
          └────────────┬────────────┘
          ┌────────────▼────────────┐
          │        Routers           │
          │  POST /shorten           │
          │  GET  /{code}            │
          │  DELETE /api/urls/{code} │
          │  GET  /analytics/*       │
          │  GET  /health, /metrics  │
          └────┬──────────┬─────────┘
               │          │
    ┌──────────▼──┐  ┌────▼──────────────┐
    │ URL Service  │  │ Analytics Service  │
    │ (url_service)│  │(analytics_service) │
    └──────┬───┬──┘  └────────┬──────────┘
           │   │              │
    ┌──────▼─┐ │         ┌───▼────────┐
    │ Cache  │ │         │ MongoDB     │
    │ (LRU)  │ └────────►│ urls coll  │
    └────────┘           │ clicks coll│
                         └────────────┘
```

---

## Component Responsibilities

| Component | File | Responsibility |
|---|---|---|
| FastAPI App | `app/main.py` | Startup, middleware, routing |
| Config | `app/config.py` | Type-safe env settings |
| URL Service | `app/services/url_service.py` | Code generation, expiry, soft-delete |
| Analytics Service | `app/services/analytics_service.py` | Click recording, aggregation |
| Cache Service | `app/services/cache_service.py` | LRU hot-path cache |
| MongoDB Layer | `app/db/mongodb.py` | Async connection with retry |
| Rate Limit MW | `app/middleware/rate_limit.py` | Sliding-window 30 req/min |
| Audit Log MW | `app/middleware/audit_log.py` | JSON logging with trace IDs |
| Orchestrator | `orchestrator/orchestrator.py` | SDLC DAG pipeline engine |

---

## Technology Choices

| Concern | Technology | Rationale |
|---|---|---|
| Web Framework | FastAPI | Async, typed, OpenAPI auto-docs |
| Database | MongoDB (motor) | Flexible schema, horizontal scale |
| ORM/Validation | Pydantic v2 | Type-safe, fast |
| Cache | In-memory LRU | Zero infra dependency |
| Config | pydantic-settings | `.env` + type safety |
| Testing | pytest + httpx | Async-compatible |
| Orchestration | Pure Python DAG | Lightweight, no external deps |

---

## Data Flow: URL Shortening

```
Client → POST /shorten
  → RateLimitMiddleware (check IP quota)
  → AuditLogMiddleware (log request + trace ID)
  → ShortenRouter
    → url_service.create_short_url()
      → Check custom alias collision in MongoDB
      → Generate unique 7-char code (if no alias)
      → Insert document into urls collection
      → Return URLResponse with short_url
  → 201 Created
```

## Data Flow: Redirect

```
Client → GET /{short_code}
  → RedirectRouter
    → url_service.resolve_url()
      → Cache HIT? → return long_url directly
      → Cache MISS → query MongoDB → cache result
      → Check expiry and is_active
    → url_service.increment_clicks() (atomic $inc)
    → analytics_service.record_click() (event to clicks collection)
  → 302 Redirect to long_url
```

---

## Key Architectural Decisions

1. **Separate `clicks` collection**: Avoids document bloat on hot URLs. Enables efficient time-range queries.
2. **LRU cache first**: Most redirects avoid DB for hot URLs. Cache TTL = 5 min.
3. **Soft-delete (`is_active`)**: Records retained for audit. No data loss.
4. **Unique index on `short_code`**: DB-level uniqueness guarantee, not application-level only.
5. **Async throughout**: Motor + FastAPI = non-blocking I/O under load.
