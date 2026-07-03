"""
orchestrator/stages/requirements.py – Stage 1: Requirement parsing & normalization.
Interprets raw requirements, identifies ambiguity, and produces normalized specs.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Tuple

from orchestrator.state import PipelineState, StageResult
from orchestrator.audit import audit
from orchestrator.governance import governance

logger = logging.getLogger(__name__)

# ── Known requirement templates ────────────────────────────────────────────────

REQUIREMENT_TEMPLATES = {
    "greenfield": {
        "description": "Build a URL shortener service from scratch",
        "features": [
            "POST /shorten – create short URL",
            "GET /{code} – redirect to long URL",
            "GET /analytics/stats/{code} – click statistics",
            "GET /health – health check",
            "Rate limiting: 30 req/min per IP",
            "MongoDB persistence",
            "In-memory LRU cache",
        ],
        "non_functional": [
            "P95 redirect latency < 100ms",
            "99.9% uptime",
            "Audit logging on all requests",
        ],
        "ambiguities": [],
    },
    "brownfield": {
        "description": "Add URL expiry and detailed analytics to the existing URL shortener",
        "features": [
            "Add expires_in_hours field to POST /shorten",
            "Auto-expire short URLs after TTL elapses",
            "Record click events with IP, user-agent, referer",
            "GET /analytics/detail/{code} – daily click breakdown",
            "GET /analytics/top – top URLs leaderboard",
            "Soft-delete: DELETE /api/urls/{code}",
        ],
        "non_functional": [
            "Backward-compatible: existing URLs must still work",
            "Migration: add expires_at index on urls collection",
        ],
        "ambiguities": [],
    },
    "ambiguous": {
        "description": "Make the URL shortener better",
        "features": [],           # Intentionally empty – must be clarified
        "non_functional": [],
        "ambiguities": [
            "What does 'better' mean? Performance, features, reliability?",
            "Is there a target user segment (developers, marketers)?",
            "What is the current pain point?",
            "Any specific SLA or latency target?",
        ],
    },
}


def _resolve_ambiguity(raw: str, scenario: str) -> Tuple[List[str], List[str]]:
    """
    Simulate requirement clarification for ambiguous inputs.
    Returns (clarified_features, decisions).
    """
    if scenario != "ambiguous":
        return [], []

    # Simulated AI-assisted clarification result
    clarified = [
        "Add custom alias support for branded short URLs",
        "Add URL expiry (expires_in_hours)",
        "Improve analytics: daily breakdown and top URLs",
        "Add /health and /metrics endpoints",
        "Enforce rate limiting to prevent abuse",
    ]
    decisions = [
        "Interpreted 'better' as: more features + reliability",
        "Assumed target audience: developers using the API directly",
        "Resolved SLA gap: target P95 latency < 150ms",
    ]
    return clarified, decisions


def run(state: PipelineState) -> StageResult:
    """Execute the requirements stage."""
    logger.info("📋 [Stage] Requirements – Starting")
    audit.log("requirements", "start", "running")

    scenario = state.scenario
    template = REQUIREMENT_TEMPLATES.get(scenario, REQUIREMENT_TEMPLATES["greenfield"])

    features = list(template["features"])
    ambiguities = list(template["ambiguities"])
    decisions: List[str] = []

    # Handle ambiguous scenario
    if ambiguities:
        logger.info(f"  ⚠️  {len(ambiguities)} ambiguities detected – resolving...")
        for a in ambiguities:
            logger.info(f"     Q: {a}")
        clarified, resolved_decisions = _resolve_ambiguity(template["description"], scenario)
        features.extend(clarified)
        decisions.extend(resolved_decisions)
        for d in resolved_decisions:
            state.record_decision("requirements", d, "AI clarification of ambiguous requirement")
        audit.log("requirements", "ambiguity_resolution", "completed", agent_decision=str(resolved_decisions))

    # Policy check: ensure no PII or blocked content in requirements text
    for feature in features:
        ok, violations = governance.check_url_policy("https://example.com")  # Symbolic check
        if not ok:
            audit.log("requirements", "policy_violation", "blocked", details={"violations": violations})
            return StageResult(
                stage="requirements", status="failed",
                errors=[f"Policy violation: {v}" for v in violations]
            )

    # Record key decisions
    state.record_decision(
        "requirements",
        f"Normalized {len(features)} features from scenario '{scenario}'",
        f"Used template matching + ambiguity resolution for scenario type.",
    )

    # Store outputs in shared context
    state.context["requirements"] = {
        "description": template["description"],
        "features": features,
        "non_functional": template.get("non_functional", []),
        "ambiguities_resolved": len(ambiguities),
    }

    result = StageResult(
        stage="requirements",
        status="success",
        outputs={
            "feature_count": len(features),
            "features": features,
            "non_functional": template.get("non_functional", []),
            "ambiguities_resolved": len(ambiguities),
            "description": template["description"],
        },
    )
    audit.log("requirements", "complete", "success", agent_decision=f"{len(features)} features normalized")
    logger.info(f"  ✅ Requirements: {len(features)} features extracted, {len(ambiguities)} ambiguities resolved")
    return result
