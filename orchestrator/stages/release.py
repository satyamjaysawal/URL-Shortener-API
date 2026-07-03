"""
orchestrator/stages/release.py – Stage 6: Release readiness gate.
Validates all upstream stages passed, requires human approval, emits release report.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from orchestrator.state import PipelineState, StageResult
from orchestrator.audit import audit
from orchestrator.governance import governance

logger = logging.getLogger(__name__)

RELEASE_CHECKLIST = [
    ("requirements", "Requirements stage succeeded"),
    ("architecture",  "Architecture stage succeeded"),
    ("implementation","Implementation stage succeeded"),
    ("testing",       "Testing stage succeeded"),
    ("documentation", "Documentation stage succeeded"),
]


def run(state: PipelineState, auto_approve: bool = False) -> StageResult:
    """Execute the release stage with human approval checkpoint."""
    logger.info("🚀 [Stage] Release – Starting")
    audit.log("release", "start", "running")

    # Validate all upstream stages passed
    violations = []
    checklist_results = []
    for stage_name, description in RELEASE_CHECKLIST:
        stage_result = state.stages.get(stage_name)
        passed = stage_result is not None and stage_result.status == "success"
        checklist_results.append({
            "check": description,
            "status": "✅ PASS" if passed else "❌ FAIL",
        })
        if not passed:
            violations.append(f"Release gate failed: {description}")

    if violations:
        logger.error("  ❌ Release checklist FAILED:")
        for v in violations:
            logger.error(f"     {v}")
        audit.log("release", "checklist", "failed", details={"violations": violations})
        return StageResult(
            stage="release",
            status="failed",
            outputs={"checklist": checklist_results},
            errors=violations,
        )

    # Print checklist
    logger.info("  📋 Release Checklist:")
    for item in checklist_results:
        logger.info(f"     {item['status']} {item['check']}")

    # Gather metrics summary for approval prompt
    test_ctx = state.context.get("testing", {})
    doc_ctx = state.context.get("documentation", {})
    impl_ctx = state.context.get("implementation", {})

    approval_summary = (
        f"Scenario: {state.scenario}\n"
        f"Artifacts: {impl_ctx.get('artifacts_verified', 'N/A')}\n"
        f"Tests: {test_ctx.get('passed', 'N/A')}/{test_ctx.get('total', 'N/A')} passed "
        f"({test_ctx.get('pass_rate', 0):.0%})\n"
        f"Docs: {doc_ctx.get('artifacts_verified', 'N/A')}/{len(RELEASE_CHECKLIST)} verified\n"
        f"All checklist items: PASSED"
    )

    # Human approval checkpoint
    approved = governance.request_approval("release", approval_summary, auto_approve=auto_approve)
    if not approved:
        audit.log("release", "approval", "rejected", human_override=True)
        return StageResult(
            stage="release",
            status="failed",
            errors=["Release rejected by human reviewer."],
        )

    state.record_decision(
        "release",
        "Release approved and pipeline completed",
        "All checklist items passed; human approval granted.",
        human_approved=True,
    )

    result = StageResult(
        stage="release",
        status="success",
        outputs={
            "checklist": checklist_results,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "scenario": state.scenario,
            "human_approved": True,
        },
    )
    audit.log("release", "complete", "success",
              agent_decision="Release approved", human_override=True)
    logger.info(f"  ✅ Release: APPROVED and pipeline complete!")
    return result
