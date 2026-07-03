"""
orchestrator/orchestrator.py – Main agentic orchestration engine.

Coordinates the full SDLC lifecycle using a non-linear DAG.
Features:
  - Stage dependency graph with parallel batch execution
  - Stateful cross-stage context (PipelineState)
  - Bounded retries (max 3) with exponential backoff
  - Rollback support on failure
  - Human approval checkpoints
  - Embedded governance guardrails
  - Audit-grade observability (JSON-L)
  - Reliability metrics (success rate, retry count, MTTR, e2e latency)
  - Dynamic re-planning when upstream stage changes
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from orchestrator.state import PipelineState, StageResult
from orchestrator.graph import DependencyGraph
from orchestrator.metrics import MetricsCollector
from orchestrator.audit import audit
from orchestrator.stages import requirements, architecture, implementation, testing, documentation, release

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [1, 2, 4]   # Exponential backoff

# Maps stage name -> stage runner function
STAGE_RUNNERS: Dict[str, Callable[[PipelineState], StageResult]] = {
    "requirements":   requirements.run,
    "architecture":   architecture.run,
    "implementation": implementation.run,
    "testing":        testing.run,
    "documentation":  documentation.run,
}


class Orchestrator:
    """
    Non-linear, stateful SDLC pipeline orchestrator.
    """

    def __init__(self, scenario: str, auto_approve: bool = True):
        self.scenario = scenario
        self.auto_approve = auto_approve
        self.run_id = str(uuid.uuid4())[:8]
        self.state = PipelineState(run_id=self.run_id, scenario=scenario)
        self.graph = DependencyGraph()
        self.metrics = MetricsCollector()
        audit.set_run(self.run_id)

    # ── Public entry point ──────────────────────────────────────────────────────

    def run(self) -> PipelineState:
        """Execute the full pipeline and return final state."""
        self._print_header()
        self.metrics.pipeline_started()

        execution_plan = self.graph.get_execution_order()
        logger.info(self.graph.describe())

        for batch in execution_plan:
            if len(batch) > 1:
                logger.info(f"\n⚡ Parallel batch: {batch}")
                self._run_parallel_batch(batch)
            else:
                stage = batch[0]
                logger.info(f"\n▶  Sequential stage: {stage}")
                self._run_stage_with_retry(stage)

            # Check for safe-stop: if a critical stage failed, halt pipeline
            if self._should_stop(batch):
                logger.error("🛑 Pipeline safe-stop triggered. Halting execution.")
                self.state.status = "failed"
                self.metrics.pipeline_ended()
                self._print_summary()
                return self.state

        self.metrics.pipeline_ended()
        self.state.status = "completed"
        self.state.completed_at = self._now_iso()
        self.state.metrics = self.metrics.generate_report()
        self.state.save()

        self._print_summary()
        return self.state

    # ── Stage execution ─────────────────────────────────────────────────────────

    def _run_stage_with_retry(self, stage: str, retry_count: int = 0) -> StageResult:
        """Run a single stage with bounded retry and rollback on failure."""
        self.metrics.stage_started(stage)
        self.state.current_stage = stage

        # Special handling for release stage (requires human approval arg)
        if stage == "release":
            result = release.run(self.state, auto_approve=self.auto_approve)
        else:
            runner = STAGE_RUNNERS.get(stage)
            if not runner:
                result = StageResult(stage=stage, status="skipped", outputs={"note": "No runner found"})
            else:
                try:
                    result = runner(self.state)
                except Exception as e:
                    logger.error(f"  💥 Stage '{stage}' raised exception: {e}", exc_info=True)
                    result = StageResult(stage=stage, status="failed", errors=[str(e)])

        result.retry_count = retry_count
        result.started_at = self._now_iso()
        result.completed_at = self._now_iso()

        if result.status == "failed" and retry_count < MAX_RETRIES:
            backoff = RETRY_BACKOFF_SECONDS[min(retry_count, len(RETRY_BACKOFF_SECONDS) - 1)]
            logger.warning(f"  ⟳  Stage '{stage}' failed. Retry {retry_count + 1}/{MAX_RETRIES} in {backoff}s...")
            self.metrics.record_retry(stage)
            audit.log(stage, "retry", f"attempt_{retry_count + 1}",
                      agent_decision=f"Retrying after failure: {result.errors[:1]}")
            time.sleep(backoff)

            # Dynamic re-planning: check if upstream context changed before retry
            self._check_upstream_changes(stage)
            return self._run_stage_with_retry(stage, retry_count + 1)

        if result.status == "failed":
            # Max retries exceeded – attempt rollback
            self._rollback_stage(stage)
            self.metrics.stage_completed(stage, "rolled_back", retry_count)
            audit.log(stage, "max_retries_exceeded", "failed",
                      agent_decision=f"Rolled back after {MAX_RETRIES} retries")
        else:
            self.metrics.stage_completed(stage, result.status, retry_count)

        self.state.set_stage_result(result)
        return result

    def _run_parallel_batch(self, stages: List[str]) -> None:
        """Run multiple stages synchronously (simulating parallel paths)."""
        results = {}
        for stage in stages:
            results[stage] = self._run_stage_with_retry(stage)

        # Synchronization point: ensure all parallel stages completed
        all_ok = all(r.status in ("success", "skipped") for r in results.values())
        if not all_ok:
            failed = [s for s, r in results.items() if r.status == "failed"]
            logger.warning(f"  ⚠️  Parallel batch partial failure: {failed}")
            audit.log("orchestrator", "parallel_sync", "partial_failure",
                      details={"failed_stages": failed})

    # ── Rollback ────────────────────────────────────────────────────────────────

    def _rollback_stage(self, stage: str) -> None:
        """Invoke stage-specific rollback if available."""
        logger.warning(f"  🔄 Rolling back stage: {stage}")
        if stage == "implementation":
            implementation.rollback(self.state)
        else:
            logger.info(f"  ℹ️  No rollback defined for stage '{stage}'")
        audit.log(stage, "rollback", "executed", agent_decision="Rollback triggered after max retries")

    # ── Safe-stop ───────────────────────────────────────────────────────────────

    def _should_stop(self, batch: List[str]) -> bool:
        """
        Halt pipeline if any stage in batch critically failed
        (except documentation, which is advisory).
        """
        advisory_stages = {"documentation"}
        for stage in batch:
            if stage in advisory_stages:
                continue
            result = self.state.stages.get(stage)
            if result and result.status in ("failed", "rolled_back"):
                return True
        return False

    # ── Dynamic re-planning ─────────────────────────────────────────────────────

    def _check_upstream_changes(self, stage: str) -> None:
        """
        Check if upstream stage outputs have changed since last run.
        If so, update shared context (simulated dynamic re-planning).
        """
        deps = self.graph.get_dependencies(stage)
        for dep in deps:
            dep_result = self.state.stages.get(dep)
            if dep_result and dep_result.status == "success":
                logger.info(f"  🔁 Re-planning '{stage}' with updated context from '{dep}'")
                audit.log(stage, "dynamic_replan", "triggered",
                          agent_decision=f"Context updated from upstream stage '{dep}'")

    # ── Utilities ───────────────────────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _print_header(self):
        print(f"\n{'═'*65}")
        print(f"  🤖 AGENTIC SDLC ORCHESTRATOR")
        print(f"  Run ID  : {self.run_id}")
        print(f"  Scenario: {self.scenario.upper()}")
        print(f"{'═'*65}\n")

    def _print_summary(self):
        report = self.metrics.generate_report()
        self.state.metrics = report
        self.state.save()
        print(f"\n{'═'*65}")
        print(f"  📊 PIPELINE SUMMARY – Run {self.run_id}")
        print(f"{'═'*65}")
        print(f"  Status       : {self.state.status.upper()}")
        print(f"  Scenario     : {self.scenario}")
        print(f"  E2E Latency  : {report['e2e_latency_seconds']}s")
        print(f"  Success Rate : {report['success_rate_pct']}%")
        print(f"  Total Retries: {report['total_retries']}")
        print(f"  Rollbacks    : {report['rollbacks']}")
        print(f"\n  Stage Details:")
        for s in report["stages"]:
            icon = "✅" if s["status"] == "success" else "❌" if s["status"] == "failed" else "🔄"
            print(f"    {icon} {s['stage']:<16} {s['status']:<12} {s['duration_seconds']}s  retries={s['retries']}")
        print(f"\n  Decisions recorded: {len(self.state.decisions)}")
        print(f"  Audit log: audit.jsonl")
        print(f"  State file: pipeline_state.json")
        print(f"{'═'*65}\n")
