# Orchestration Model – Agentic SDLC Engine

## Overview

This project has **two orchestration layers**:

1. **SDLC Orchestrator** (`orchestrator/orchestrator.py`) – Full software lifecycle DAG (Requirements → Release)
2. **LangGraph AI Agent** (`app/services/agent_service.py`) – Real-time URL analysis workflow powered by Gemini

| Layer | Purpose | Live UI |
|---|---|---|
| SDLC Orchestrator | Build/test/document the system itself | `/orchestrator` page |
| LangGraph Agent | Analyze URLs at runtime | Home → AI Analyzer tab |

**Live app:** https://frontend-dun-chi-79.vercel.app  
**API:** https://backend-six-pied-13.vercel.app

---

## LangGraph AI Agent Workflow

```
[Entry] → [analyze_url] → [governance_router] → [suggest_alias] → [END]
                               ↓ unsafe
                              [END]
```

| Node | Type | Description |
|---|---|---|
| `analyze_url` | Agent | Gemini structured output: category, safety_status, tags |
| `governance_router` | Gate | Blocks unsafe URLs (403); routes safe URLs to alias agent |
| `suggest_alias` | Agent | Generates 4–6 char alias (skipped if custom alias provided) |

**Streaming:** `POST /ai/analyze/stream` emits SSE events (`node_start`, `node_complete`, `governance_decision`, `workflow_complete`) consumed by the frontend `AgentFlowGraph` component.

**API key:** Per-request `gemini_api_key` from the user session overrides the server `.env` key.

---

## SDLC Orchestrator

The orchestration engine (`orchestrator/orchestrator.py`) implements a **non-linear, stateful SDLC pipeline** using a Directed Acyclic Graph (DAG). It coordinates all lifecycle stages from Requirements through Release with governance, retry logic, and human approval checkpoints.

---

## Pipeline DAG

```
[Requirements]
      │
      ▼
[Architecture]
      │
      ▼
[Implementation]
      │
      ├──────────────────────┐
      ▼                      ▼
  [Testing]          [Documentation]    ← Parallel batch
      │                      │
      └──────────┬───────────┘
                 ▼
           [Release Gate]
           (Human approval)
```

### Stage Descriptions

| Stage | Purpose | Entry Gate | Exit Gate |
|---|---|---|---|
| Requirements | Parse intent, resolve ambiguity | None | ≥1 feature extracted |
| Architecture | Generate ADRs, data model, component design | `architecture_rationale` in context | ≥4 ADRs recorded |
| Implementation | Verify all code artifacts present | `implementation_plan` in context | All files pass quality threshold |
| Testing | Run pytest, enforce pass rate | Artifacts exist | ≥70% pass rate |
| Documentation | Verify all docs present | None (advisory) | All docs present |
| Release | Release readiness gate | All upstreams succeeded | Human approval granted |

---

## Key Orchestration Features

### 1. Non-Linear DAG Execution
Stages run in topological batches. `testing` and `documentation` run in **parallel** because they share no dependency between them.

### 2. Stateful Cross-Stage Context
`PipelineState` persists shared context across all stages:
- `context["requirements"]` → consumed by architecture
- `context["architecture"]` → consumed by implementation
- `context["testing"]` → consumed by release checklist

State is serialized to `pipeline_state.json` after every run.

### 3. Bounded Retry with Exponential Backoff
```
MAX_RETRIES = 3
Backoff = [1s, 2s, 4s]
```
Each stage retries up to 3 times on failure. After max retries, rollback is triggered.

### 4. Dynamic Re-Planning
Before each retry, the orchestrator checks if upstream stage outputs have changed and updates the shared context accordingly.

### 5. Human Approval Checkpoint
The `release` stage **always** requires explicit approval:
```
⚠️  HUMAN APPROVAL REQUIRED: Stage 'RELEASE'
Approve? [y/N]:
```
In non-interactive/CI mode, `auto_approve=True` bypasses the prompt (configurable).

### 6. Rollback Support
If a stage fails after all retries, `rollback()` is called:
- `implementation` rollback: flags artifacts for removal
- Other stages: logs intent (stateless rollback)

### 7. Safe-Stop
If a non-advisory stage fails (even after rollback), the pipeline halts immediately. `documentation` is advisory and does not trigger safe-stop.

### 8. Governance Guardrails
- **URL policy**: blocks internal IPs, localhost, PII keywords
- **Stage entry gates**: require context keys before proceeding
- **Schema change control**: requires rationale for DB schema changes
- **Change control**: human approval for release

---

## Observability

### Audit Log (`audit.jsonl`)
Every action is written to a JSON-Lines file:
```json
{"timestamp": "...", "run_id": "abc12345", "stage": "requirements",
 "action": "complete", "outcome": "success",
 "agent_decision": "7 features normalized", "human_override": false}
```

### Metrics Report
Generated at pipeline end:
```json
{
  "total_stages": 6,
  "succeeded": 6,
  "failed": 0,
  "rollbacks": 0,
  "total_retries": 0,
  "success_rate_pct": 100.0,
  "e2e_latency_seconds": 2.145,
  "stages": [...]
}
```

### Decision Lineage
All agent decisions are recorded in `PipelineState.decisions[]`:
```python
Decision(stage="requirements", description="...", rationale="...", human_approved=False)
```

---

## Three Scenarios

| Scenario | Starting Point | Key Behavior |
|---|---|---|
| **Greenfield** | Empty slate | Full DAG from scratch |
| **Brownfield** | Existing `main.py` | Impact analysis, schema change gate |
| **Ambiguous** | Vague requirement | Clarification loop before pipeline |
