"""
orchestrator/metrics.py – Reliability metrics collection per pipeline run.
Tracks: success rate, retry count, MTTR, end-to-end latency.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class StageMetric:
    stage: str
    started_at: float = 0.0
    completed_at: float = 0.0
    status: str = "pending"   # success | failed | rolled_back
    retry_count: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.completed_at and self.started_at:
            return round(self.completed_at - self.started_at, 3)
        return 0.0


class MetricsCollector:
    """Collects per-stage and pipeline-level reliability metrics."""

    def __init__(self):
        self._pipeline_start: float = 0.0
        self._pipeline_end: float = 0.0
        self._stages: Dict[str, StageMetric] = {}
        self._rollbacks: int = 0

    def pipeline_started(self):
        self._pipeline_start = time.monotonic()

    def pipeline_ended(self):
        self._pipeline_end = time.monotonic()

    def stage_started(self, stage: str):
        self._stages[stage] = StageMetric(stage=stage, started_at=time.monotonic())

    def stage_completed(self, stage: str, status: str, retry_count: int = 0):
        m = self._stages.get(stage, StageMetric(stage=stage))
        m.completed_at = time.monotonic()
        m.status = status
        m.retry_count = retry_count
        self._stages[stage] = m
        if status == "rolled_back":
            self._rollbacks += 1

    def record_retry(self, stage: str):
        if stage in self._stages:
            self._stages[stage].retry_count += 1

    def generate_report(self) -> dict:
        """Produce a summary reliability report."""
        total = len(self._stages)
        succeeded = sum(1 for m in self._stages.values() if m.status == "success")
        failed = sum(1 for m in self._stages.values() if m.status == "failed")
        total_retries = sum(m.retry_count for m in self._stages.values())
        e2e_latency = round(self._pipeline_end - self._pipeline_start, 3) if self._pipeline_end else 0.0
        success_rate = round(succeeded / total * 100, 1) if total else 0.0

        stage_details = [
            {
                "stage": m.stage,
                "status": m.status,
                "duration_seconds": m.duration_seconds,
                "retries": m.retry_count,
            }
            for m in self._stages.values()
        ]

        return {
            "total_stages": total,
            "succeeded": succeeded,
            "failed": failed,
            "rollbacks": self._rollbacks,
            "total_retries": total_retries,
            "success_rate_pct": success_rate,
            "e2e_latency_seconds": e2e_latency,
            "stages": stage_details,
        }
