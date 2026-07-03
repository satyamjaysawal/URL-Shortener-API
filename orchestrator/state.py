"""
orchestrator/state.py – Stateful pipeline context manager.
Persists cross-stage state and decision lineage to a JSON file.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

STATE_FILE = "pipeline_state.json"


@dataclass
class Decision:
    """A single agent decision recorded in lineage."""
    stage: str
    description: str
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    human_approved: bool = False


@dataclass
class StageResult:
    """Output of a completed pipeline stage."""
    stage: str
    status: str          # "success" | "failed" | "skipped" | "rolled_back"
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0


@dataclass
class PipelineState:
    """Full state of a pipeline run. Persisted between stages."""
    run_id: str
    scenario: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    current_stage: str = "requirements"
    status: str = "running"   # running | completed | failed | stopped
    stages: Dict[str, StageResult] = field(default_factory=dict)
    decisions: List[Decision] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)  # Shared cross-stage context
    metrics: Dict[str, Any] = field(default_factory=dict)

    # ── Mutation helpers ────────────────────────────────────────────────────────

    def record_decision(self, stage: str, description: str, rationale: str, human_approved: bool = False):
        self.decisions.append(Decision(
            stage=stage,
            description=description,
            rationale=rationale,
            human_approved=human_approved,
        ))

    def set_stage_result(self, result: StageResult):
        self.stages[result.stage] = result

    def get_stage_output(self, stage: str, key: str, default=None):
        return self.stages.get(stage, StageResult(stage=stage, status="pending")).outputs.get(key, default)

    # ── Persistence ─────────────────────────────────────────────────────────────

    def save(self, path: str = STATE_FILE):
        data = asdict(self)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(f"Pipeline state saved to {path}")

    @classmethod
    def load(cls, path: str = STATE_FILE) -> "PipelineState":
        if not os.path.exists(path):
            raise FileNotFoundError(f"State file not found: {path}")
        with open(path) as f:
            data = json.load(f)
        state = cls(run_id=data["run_id"], scenario=data["scenario"])
        state.__dict__.update(data)
        # Re-hydrate nested dataclasses
        state.decisions = [Decision(**d) for d in data.get("decisions", [])]
        state.stages = {
            k: StageResult(**v) for k, v in data.get("stages", {}).items()
        }
        return state
