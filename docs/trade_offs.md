# Trade-offs, Risks & Limitations

## Live Deployment

| Component | URL |
|---|---|
| Frontend | https://frontend-dun-chi-79.vercel.app |
| Backend | https://backend-six-pied-13.vercel.app |
| GitHub (backend) | https://github.com/satyamjaysawal/URL-Shortener-API |
| GitHub (frontend) | https://github.com/satyamjaysawal/url-shortener-frontend |

---

## Trade-offs

### 1. In-Memory Cache vs Redis
- **Choice**: In-memory LRU cache
- **Trade-off**: No cross-process sharing. Multiple instances = cache misses.
- **Mitigation**: Redis adapter path documented; swap in `cache_service.py`
- **When to switch**: When deploying >1 uvicorn worker or multiple pods

### 2. MongoDB vs PostgreSQL
- **Choice**: MongoDB
- **Trade-off**: No native foreign keys; eventual consistency in replica sets
- **Benefit**: Flexible schema for URL documents; easy horizontal sharding
- **When to switch**: If strong relational analytics are needed

### 3. In-Process Rate Limiting vs Redis Rate Limiting
- **Choice**: Sliding-window in-memory (per process)
- **Trade-off**: Multi-process deployments get independent quotas per worker
- **Mitigation**: For production, use NGINX rate limiting or Redis-backed sliding window

### 4. Separate Clicks Collection vs Embedded Array
- **Choice**: Separate `clicks` collection
- **Trade-off**: Extra write per redirect (slight latency increase ~1ms)
- **Benefit**: Avoids MongoDB document size limit on hot URLs; enables efficient time-range queries

### 5. Soft-Delete vs Hard-Delete
- **Choice**: Soft-delete (`is_active = false`)
- **Trade-off**: Data accumulates over time
- **Benefit**: Audit trail preserved; no data loss; can reactivate

---

## Risks

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| MongoDB connection failure | High | Low | Retry with exponential backoff (3 attempts) |
| Short code collision | Low | Very Low | Unique index + 5-attempt loop |
| Cache poisoning | Medium | Low | TTL expiry + cache invalidation on delete |
| Rate limit bypass (proxy) | Medium | Medium | NGINX-level rate limiting in production |
| URL expiry race condition | Low | Low | Expiry checked on each request (not cached) |
| Audit log disk fill | Low | Low | Log rotation policy needed in production |

---

## Limitations

1. **No authentication**: API is open. Production should add API key or JWT auth.
2. **No geolocation**: `country` field reserved but not populated (requires GeoIP service).
3. **No URL validation against blocklists**: Malicious URLs are not screened against threat feeds.
4. **Single-process caching**: Cache is not shared across multiple uvicorn workers.
5. **SDLC orchestrator vs runtime AI**: The SDLC orchestrator (`orchestrator/`) uses deterministic logic for pipeline stages. Runtime URL analysis uses Gemini via LangGraph (`agent_service.py`).
6. **User API keys in session**: Frontend stores optional Gemini keys in `sessionStorage` — cleared on tab close, not encrypted at rest.
7. **No persistent session for orchestrator**: Pipeline state written to local file (not a proper state store like Redis or DB).
8. **Analytics at scale**: Current analytics aggregation loads all click events into memory. At >1M clicks, this should use MongoDB aggregation pipelines.
9. **Gemini dependency**: AI features require a valid `GOOGLE_API_KEY` on the server or a user-provided key. Vercel cold starts may add latency to first AI request.

---

## Scalability Considerations

| Component | Current Limit | Scale-Up Path |
|---|---|---|
| API | Single process ~500 RPS | Gunicorn multi-worker + NGINX |
| Cache | 1000 entries in-memory | Redis cluster |
| DB reads | MongoDB single node | Read replicas |
| Analytics | In-memory aggregation | MongoDB `$group` aggregation pipeline |
| Rate limiting | In-process per worker | Redis INCR sliding window |

---

## Validation Approach

- **Unit tests**: Code generation, cache eviction, URL validation, governance, metrics
- **Integration tests**: Model shapes, cache behavior, config defaults, governance chains
- **E2E tests**: Full pipeline per scenario (greenfield, brownfield, ambiguous)
- **Manual**: FastAPI `/docs` UI, curl smoke tests, orchestrator CLI

---

## Assumptions

1. MongoDB Atlas connection string is pre-provisioned in `.env`
2. Short URLs are ephemeral (no SLA on persistence after expiry)
3. Analytics are best-effort (fire-and-forget click recording)
4. The orchestrator runs in a trusted environment (no sandboxing of agent decisions)
