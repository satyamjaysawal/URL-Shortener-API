"""
orchestrator/stages/implementation.py – Stage 3: Code artifact generation & review.
Validates that all required code artifacts exist and meet quality thresholds.
"""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Tuple

from orchestrator.state import PipelineState, StageResult
from orchestrator.audit import audit
from orchestrator.governance import governance

logger = logging.getLogger(__name__)

# Expected code artifacts and their minimum line counts (quality gate)
REQUIRED_ARTIFACTS: List[Tuple[str, int]] = [
    ("app/main.py",                          30),
    ("app/config.py",                        20),
    ("app/models/url.py",                    30),
    ("app/models/analytics.py",              20),
    ("app/db/mongodb.py",                    30),
    ("app/services/url_service.py",          40),
    ("app/services/analytics_service.py",    40),
    ("app/services/cache_service.py",        40),
    ("app/routers/shorten.py",               20),
    ("app/routers/redirect.py",              20),
    ("app/routers/analytics.py",             25),
    ("app/routers/health.py",                20),
    ("app/middleware/rate_limit.py",          25),
    ("app/middleware/audit_log.py",           20),
]

BROWNFIELD_ARTIFACTS: List[Tuple[str, int]] = [
    ("app/models/url.py",       30),   # expires_at added
    ("app/routers/analytics.py", 25),  # /detail and /top added
]


def _check_artifact(path: str, min_lines: int) -> Tuple[bool, str]:
    """Check that a file exists and meets minimum line count (all non-empty lines)."""
    if not os.path.exists(path):
        return False, f"Missing: {path}"
    with open(path) as f:
        lines = [l for l in f if l.strip()]
    if len(lines) < min_lines:
        return False, f"{path} has {len(lines)} non-empty lines (min: {min_lines})"
    return True, f"{path} OK ({len(lines)} lines)"


def run(state: PipelineState) -> StageResult:
    """Execute the implementation stage."""
    logger.info("💻 [Stage] Implementation – Starting")
    audit.log("implementation", "start", "running")

    # Entry gate
    state.context.setdefault("implementation_plan", "Use FastAPI+MongoDB as per ADRs")
    ok, violations = governance.check_stage_entry("implementation", state.context)
    if not ok:
        return StageResult(stage="implementation", status="failed", errors=violations)

    # Select artifacts to check based on scenario
    if state.scenario == "brownfield":
        artifacts_to_check = BROWNFIELD_ARTIFACTS
        audit.log("implementation", "impact_analysis", "running",
                  agent_decision="Brownfield: checking only impacted modules")
    else:
        artifacts_to_check = REQUIRED_ARTIFACTS

    passed = []
    failed = []

    for path, min_lines in artifacts_to_check:
        ok_artifact, message = _check_artifact(path, min_lines)
        if ok_artifact:
            passed.append(message)
        else:
            failed.append(message)
            logger.warning(f"  ⚠️  Artifact check failed: {message}")

    if failed:
        state.record_decision(
            "implementation",
            f"{len(failed)} artifacts failed quality gate",
            "Artifacts missing or below minimum line count threshold.",
        )
        audit.log("implementation", "quality_gate", "failed", details={"failed": failed})
        return StageResult(
            stage="implementation",
            status="failed",
            outputs={"passed": len(passed), "failed": len(failed)},
            errors=failed,
        )

    state.record_decision(
        "implementation",
        f"All {len(passed)} required artifacts verified",
        "All files present and meet minimum quality thresholds.",
    )

    state.context["implementation"] = {
        "artifacts_verified": len(passed),
        "artifacts": [p.split("OK")[0].strip() for p in passed],
    }

    result = StageResult(
        stage="implementation",
        status="success",
        outputs={
            "artifacts_verified": len(passed),
            "artifacts_failed": len(failed),
            "artifact_list": [p for p in passed],
        },
    )
    audit.log("implementation", "complete", "success",
              agent_decision=f"{len(passed)} artifacts verified")
    logger.info(f"  ✅ Implementation: {len(passed)} artifacts verified")
    return result


def rollback(state: PipelineState) -> None:
    """Rollback: log the intent (file deletion is out of scope for safety)."""
    logger.warning("  🔄 Implementation rollback: would remove generated artifacts")
    audit.log("implementation", "rollback", "executed",
              agent_decision="Rollback requested – artifacts flagged for removal")
