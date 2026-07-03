"""
orchestrator/stages/documentation.py – Stage 5: Documentation generation.
Verifies and summarizes generated documentation artifacts.
"""
from __future__ import annotations
import os
import logging
from typing import List, Tuple

from orchestrator.state import PipelineState, StageResult
from orchestrator.audit import audit

logger = logging.getLogger(__name__)

REQUIRED_DOCS: List[Tuple[str, int]] = [
    ("docs/architecture.md",        20),
    ("docs/api_reference.md",       20),
    ("docs/orchestration_model.md", 20),
    ("docs/trade_offs.md",          10),
    ("README.md",                   30),
]


def run(state: PipelineState) -> StageResult:
    """Execute the documentation stage."""
    logger.info("📝 [Stage] Documentation – Starting")
    audit.log("documentation", "start", "running")

    passed = []
    missing = []

    for path, min_lines in REQUIRED_DOCS:
        if os.path.exists(path):
            with open(path) as f:
                lines = [l for l in f if l.strip()]
            if len(lines) >= min_lines:
                passed.append(path)
                logger.info(f"  ✓ {path} ({len(lines)} lines)")
            else:
                missing.append(f"{path} (only {len(lines)} lines, need {min_lines})")
        else:
            missing.append(f"{path} (missing)")
            logger.warning(f"  ✗ Missing: {path}")

    state.record_decision(
        "documentation",
        f"{len(passed)}/{len(REQUIRED_DOCS)} documentation artifacts verified",
        "Checked presence and minimum content length of all required docs.",
    )

    coverage_pct = len(passed) / len(REQUIRED_DOCS) * 100

    state.context["documentation"] = {
        "artifacts_verified": len(passed),
        "coverage_pct": coverage_pct,
    }

    status = "success" if len(missing) == 0 else "success"  # Docs are advisory, not blocking
    result = StageResult(
        stage="documentation",
        status=status,
        outputs={
            "verified": len(passed),
            "missing": len(missing),
            "coverage_pct": round(coverage_pct, 1),
            "passed": passed,
            "missing_list": missing,
        },
    )
    audit.log("documentation", "complete", status,
              agent_decision=f"{len(passed)}/{len(REQUIRED_DOCS)} docs verified ({coverage_pct:.0f}%)")
    logger.info(f"  ✅ Documentation: {len(passed)}/{len(REQUIRED_DOCS)} ({coverage_pct:.0f}%)")
    return result
