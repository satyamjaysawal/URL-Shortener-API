"""
orchestrator/stages/testing.py – Stage 4: Test execution and validation.
Runs pytest and enforces a minimum pass-rate threshold.
"""
from __future__ import annotations
import subprocess
import sys
import logging
import os

from orchestrator.state import PipelineState, StageResult
from orchestrator.audit import audit

logger = logging.getLogger(__name__)

PASS_RATE_THRESHOLD = 0.70  # 70% tests must pass to proceed


def run(state: PipelineState) -> StageResult:
    """Execute the testing stage."""
    logger.info("🧪 [Stage] Testing – Starting")
    audit.log("testing", "start", "running")

    tests_dir = "tests"
    if not os.path.isdir(tests_dir):
        audit.log("testing", "skip", "no_tests_found")
        return StageResult(
            stage="testing", status="success",
            outputs={"note": "No tests directory found – skipped"},
        )

    # Run pytest and capture output
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", tests_dir, "-v", "--tb=short", "--no-header", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        return StageResult(
            stage="testing", status="failed",
            errors=["pytest timed out after 120 seconds"],
        )
    except FileNotFoundError:
        return StageResult(
            stage="testing", status="failed",
            errors=["pytest not found – install with: pip install pytest"],
        )

    # Parse results from pytest output
    passed = stdout.count(" PASSED") + stdout.count(" passed")
    failed_count = stdout.count(" FAILED") + stdout.count(" failed")
    errors_count = stdout.count(" ERROR")
    total = passed + failed_count + errors_count

    pass_rate = passed / total if total > 0 else 0.0
    passed_threshold = pass_rate >= PASS_RATE_THRESHOLD

    log_output = (stdout + "\n" + stderr).strip()
    logger.info(f"  Tests: {passed} passed, {failed_count} failed, {errors_count} errors")
    logger.info(f"  Pass rate: {pass_rate:.0%} (threshold: {PASS_RATE_THRESHOLD:.0%})")

    state.record_decision(
        "testing",
        f"Test suite: {passed}/{total} passed ({pass_rate:.0%})",
        f"Threshold: {PASS_RATE_THRESHOLD:.0%}. {'PASSED' if passed_threshold else 'FAILED'} gate.",
    )

    if not passed_threshold and total > 0:
        audit.log("testing", "quality_gate", "failed",
                  details={"passed": passed, "failed": failed_count, "pass_rate": pass_rate})
        return StageResult(
            stage="testing",
            status="failed",
            outputs={"passed": passed, "failed": failed_count, "total": total, "pass_rate": pass_rate},
            errors=[f"Pass rate {pass_rate:.0%} below threshold {PASS_RATE_THRESHOLD:.0%}", log_output[-2000:]],
        )

    state.context["testing"] = {
        "passed": passed,
        "failed": failed_count,
        "total": total,
        "pass_rate": pass_rate,
    }

    result = StageResult(
        stage="testing",
        status="success",
        outputs={
            "passed": passed,
            "failed": failed_count,
            "total": total,
            "pass_rate": round(pass_rate, 3),
            "pytest_exit_code": result.returncode,
        },
    )
    audit.log("testing", "complete", "success",
              agent_decision=f"{passed}/{total} tests passed ({pass_rate:.0%})")
    logger.info(f"  ✅ Testing: {passed}/{total} passed ({pass_rate:.0%})")
    return result
