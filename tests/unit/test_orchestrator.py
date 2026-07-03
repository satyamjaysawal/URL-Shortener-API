"""
tests/unit/test_orchestrator.py – Unit tests for orchestration components.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Dependency graph ───────────────────────────────────────────────────────────

def test_dag_execution_order():
    """DAG should produce a valid topological order."""
    from orchestrator.graph import DependencyGraph
    dag = DependencyGraph()
    batches = dag.get_execution_order()
    flat = [stage for batch in batches for stage in batch]
    # Requirements must come before architecture
    assert flat.index("requirements") < flat.index("architecture")
    assert flat.index("architecture") < flat.index("implementation")
    assert flat.index("implementation") < flat.index("release")


def test_dag_parallel_batch():
    """Testing and documentation should be in the same parallel batch."""
    from orchestrator.graph import DependencyGraph
    dag = DependencyGraph()
    batches = dag.get_execution_order()
    parallel_stages = set()
    for batch in batches:
        if len(batch) > 1:
            parallel_stages.update(batch)
    assert "testing" in parallel_stages
    assert "documentation" in parallel_stages


def test_dag_no_cycles():
    """Adding a valid DAG should not cause cycle errors."""
    from orchestrator.graph import DependencyGraph
    dag = DependencyGraph()
    # Should not raise
    batches = dag.get_execution_order()
    assert len(batches) > 0


def test_dag_describe():
    """Describe method should return a non-empty string."""
    from orchestrator.graph import DependencyGraph
    dag = DependencyGraph()
    description = dag.describe()
    assert "SDLC" in description
    assert "Batch" in description


# ── Pipeline state ─────────────────────────────────────────────────────────────

def test_pipeline_state_decision_recording():
    """Decisions should be recorded in the state."""
    from orchestrator.state import PipelineState
    state = PipelineState(run_id="test-001", scenario="greenfield")
    state.record_decision("requirements", "Feature X added", "User requested it")
    assert len(state.decisions) == 1
    assert state.decisions[0].stage == "requirements"
    assert state.decisions[0].description == "Feature X added"


def test_pipeline_state_context():
    """Context should be retrievable across stages."""
    from orchestrator.state import PipelineState
    state = PipelineState(run_id="test-002", scenario="brownfield")
    state.context["key"] = "value"
    assert state.get_stage_output("nonexistent", "key", "default") == "default"


def test_pipeline_state_save_load(tmp_path):
    """State should be serializable and loadable."""
    from orchestrator.state import PipelineState, StageResult
    state_file = str(tmp_path / "test_state.json")
    state = PipelineState(run_id="test-003", scenario="greenfield")
    state.context["feature_count"] = 7
    state.set_stage_result(StageResult(stage="requirements", status="success", outputs={"count": 7}))
    state.save(state_file)

    loaded = PipelineState.load(state_file)
    assert loaded.run_id == "test-003"
    assert loaded.scenario == "greenfield"
    assert loaded.context["feature_count"] == 7
    assert loaded.stages["requirements"].status == "success"


# ── Governance ─────────────────────────────────────────────────────────────────

def test_governance_blocks_internal_ip():
    """URLs targeting internal IPs should be blocked."""
    from orchestrator.governance import GovernanceEngine
    gov = GovernanceEngine()
    ok, violations = gov.check_url_policy("http://192.168.1.1/admin")
    assert not ok
    assert len(violations) > 0


def test_governance_blocks_localhost():
    """URLs targeting localhost should be blocked."""
    from orchestrator.governance import GovernanceEngine
    gov = GovernanceEngine()
    ok, violations = gov.check_url_policy("http://localhost:8080/secret")
    assert not ok


def test_governance_allows_valid_url():
    """Valid public URLs should pass policy."""
    from orchestrator.governance import GovernanceEngine
    gov = GovernanceEngine()
    ok, violations = gov.check_url_policy("https://www.google.com")
    assert ok
    assert len(violations) == 0


def test_governance_schema_change_requires_rationale():
    """Schema changes must have a rationale."""
    from orchestrator.governance import GovernanceEngine
    gov = GovernanceEngine()
    ok, violations = gov.check_schema_change("add expires_at", "")
    assert not ok


def test_governance_schema_change_with_rationale():
    """Schema changes with sufficient rationale should pass."""
    from orchestrator.governance import GovernanceEngine
    gov = GovernanceEngine()
    ok, violations = gov.check_schema_change("add expires_at", "Required for URL expiry feature")
    assert ok


# ── Metrics ────────────────────────────────────────────────────────────────────

def test_metrics_success_rate():
    """Success rate should be 100% when all stages succeed."""
    from orchestrator.metrics import MetricsCollector
    m = MetricsCollector()
    m.pipeline_started()
    for stage in ["requirements", "architecture", "implementation"]:
        m.stage_started(stage)
        m.stage_completed(stage, "success")
    m.pipeline_ended()
    report = m.generate_report()
    assert report["success_rate_pct"] == 100.0
    assert report["total_retries"] == 0


def test_metrics_retry_tracking():
    """Retry count should be accurately tracked."""
    from orchestrator.metrics import MetricsCollector
    m = MetricsCollector()
    m.pipeline_started()
    m.stage_started("testing")
    m.record_retry("testing")
    m.record_retry("testing")
    m.stage_completed("testing", "success", retry_count=2)
    m.pipeline_ended()
    report = m.generate_report()
    assert report["total_retries"] == 2


def test_metrics_rollback_tracking():
    """Rollback count should be tracked separately."""
    from orchestrator.metrics import MetricsCollector
    m = MetricsCollector()
    m.pipeline_started()
    m.stage_started("implementation")
    m.stage_completed("implementation", "rolled_back")
    m.pipeline_ended()
    report = m.generate_report()
    assert report["rollbacks"] == 1
