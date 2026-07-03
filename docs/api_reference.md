# API Reference – URL Shortener

## Base URLs

| Environment | URL |
|---|---|
| **Production** | https://backend-six-pied-13.vercel.app |
| **Local** | http://localhost:8000 |
| **Swagger UI** | https://backend-six-pied-13.vercel.app/docs |

**Frontend:** https://frontend-dun-chi-79.vercel.app

---

## POST /shorten

**Create a short URL** (optionally uses AI for smart alias when no custom alias is provided)

```http
POST /shorten
Content-Type: application/json
```

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `long_url` | string | ✅ | Original URL (must start with http:// or https://) |
| `custom_alias` | string | ❌ | Custom short code (3–30 alphanumeric chars) |
| `expires_in_hours` | integer | ❌ | TTL in hours (1–8760) |
| `gemini_api_key` | string | ❌ | Optional user Gemini API key for AI alias suggestion |

```json
{
  "long_url": "https://www.example.com/very/long/path?q=1",
  "custom_alias": "my-link",
  "expires_in_hours": 48
}
```

### Response – 201 Created

```json
{
  "short_url": "https://backend-six-pied-13.vercel.app/my-link",
  "short_code": "my-link",
  "long_url": "https://www.example.com/very/long/path?q=1",
  "created_at": "2026-07-03T11:00:00Z",
  "expires_at": "2026-07-05T11:00:00Z"
}
```

### Error Responses

| Status | Reason |
|---|---|
| 403 | URL flagged unsafe by AI governance |
| 409 | Custom alias already taken |
| 422 | Validation error (invalid URL, alias, or expiry) |
| 429 | Rate limit exceeded (30 req/min per IP) |
| 500 | Failed to generate unique code |

---

## POST /ai/analyze

**Analyze a URL with Gemini AI** (no short URL created)

```http
POST /ai/analyze
Content-Type: application/json
```

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `long_url` | string | ✅ | URL to analyze |
| `gemini_api_key` | string | ❌ | Optional user Gemini API key |

```json
{
  "long_url": "https://github.com/satyamjaysawal/URL-Shortener-API",
  "gemini_api_key": "optional-user-key"
}
```

### Response – 200 OK

```json
{
  "long_url": "https://github.com/satyamjaysawal/URL-Shortener-API",
  "category": "Technology",
  "safety_status": "safe",
  "tags": ["github", "open-source", "api"],
  "suggested_alias": "ghapi",
  "safe_to_shorten": true,
  "model": "gemini-2.5-flash"
}
```

### Error Responses

| Status | Reason |
|---|---|
| 422 | Invalid URL format |
| 503 | AI service unavailable (Gemini error) |

---

## POST /ai/analyze/stream

**Stream LangGraph agent workflow via Server-Sent Events**

```http
POST /ai/analyze/stream
Content-Type: application/json
Accept: text/event-stream
```

### Request Body

Same as `POST /ai/analyze`.

### SSE Event Types

| Event | Description |
|---|---|
| `workflow_start` | Agent graph execution begins |
| `node_start` | A LangGraph node begins processing |
| `node_complete` | Node finished with output data |
| `governance_decision` | Governance router decision (safe/unsafe) |
| `workflow_complete` | Final analysis result |
| `error` | Stream failure |

### Example Event

```
data: {"event": "node_complete", "node": "analyze_url", "output": {"category": "Technology", "safety_status": "safe", "tags": ["api"]}}

data: {"event": "workflow_complete", "result": {"category": "Technology", "safety_status": "safe", "suggested_alias": "ghapi", "safe_to_shorten": true}}
```

---

## GET /{short_code}

**Redirect to original URL**

```http
GET /abc1234
```

### Response – 302 Found

Redirects to the `long_url`. Records IP, user-agent, and referer.

### Error Responses

| Status | Reason |
|---|---|
| 404 | Short code not found, expired, or inactive |

---

## DELETE /api/urls/{short_code}

**Soft-delete a short URL**

```http
DELETE /api/urls/abc1234
```

### Response – 200 OK

```json
{
  "message": "Short URL 'abc1234' has been deactivated.",
  "short_code": "abc1234"
}
```

---

## GET /analytics/stats/{short_code}

**Basic click statistics**

### Response – 200 OK

```json
{
  "short_code": "abc1234",
  "long_url": "https://example.com",
  "clicks": 42,
  "is_active": true,
  "created_at": "2026-07-03T11:00:00Z",
  "expires_at": null,
  "short_url": "https://backend-six-pied-13.vercel.app/abc1234"
}
```

---

## GET /analytics/detail/{short_code}

**Full analytics breakdown**

### Response – 200 OK

```json
{
  "short_code": "abc1234",
  "long_url": "https://example.com",
  "total_clicks": 42,
  "clicks_last_7_days": 15,
  "clicks_last_30_days": 38,
  "daily_breakdown": [
    { "date": "2026-07-01", "clicks": 12 },
    { "date": "2026-07-02", "clicks": 10 }
  ],
  "top_referers": [
    { "referer": "https://twitter.com", "count": 18 }
  ],
  "is_active": true,
  "created_at": "2026-07-03T11:00:00Z",
  "expires_at": null
}
```

---

## GET /analytics/top

**Top URLs by click count**

Query params: `limit` (1–100, default 10)

### Response – 200 OK

```json
[
  {
    "short_code": "abc1234",
    "short_url": "https://backend-six-pied-13.vercel.app/abc1234",
    "long_url": "https://example.com",
    "clicks": 100,
    "created_at": "2026-07-01T00:00:00Z"
  }
]
```

---

## GET /health

**Service health check**

```json
{
  "status": "ok",
  "database": "healthy",
  "uptime_seconds": 3600.5,
  "version": "1.0.0"
}
```

---

## GET /metrics

**Cache and reliability metrics**

```json
{
  "uptime_seconds": 3600.5,
  "cache": {
    "size": 245,
    "max_size": 1000,
    "hits": 1842,
    "misses": 300,
    "hit_rate_pct": 86.01
  }
}
```

---

## Common Headers

Every response includes:
- `X-Trace-ID`: Unique UUID for this request
- `X-Response-Time-Ms`: Processing time in milliseconds