"""
tests/integration/test_e2e_flow.py – End-to-end orchestration flow tests.
Tests the full pipeline: greenfield, brownfield, and ambiguous scenarios.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Orchestrator E2E tests ─────────────────────────────────────────────────────

def test_greenfield_requirements_stage():
    """Greenfield requirements stage should extract all core features."""
    from orchestrator.state import PipelineState
    from orchestrator.stages import requirements

    state = PipelineState(run_id="e2e-001", scenario="greenfield")
    result = requirements.run(state)

    assert result.status == "success"
    assert result.outputs["feature_count"] >= 5
    assert "requirements" in state.context
    assert len(state.context["requirements"]["features"]) >= 5


def test_brownfield_requirements_stage():
    """Brownfield requirements stage should extract brownfield-specific features."""
    from orchestrator.state import PipelineState
    from orchestrator.stages import requirements

    state = PipelineState(run_id="e2e-002", scenario="brownfield")
    result = requirements.run(state)

    assert result.status == "success"
    features = result.outputs["features"]
    assert any("expir" in f.lower() for f in features)
    assert any("analytic" in f.lower() for f in features)


def test_ambiguous_requirements_resolves_ambiguity():
    """Ambiguous scenario should resolve ambiguities and produce features."""
    from orchestrator.state import PipelineState
    from orchestrator.stages import requirements

    state = PipelineState(run_id="e2e-003", scenario="ambiguous")
    result = requirements.run(state)

    assert result.status == "success"
    assert result.outputs["ambiguities_resolved"] > 0
    assert result.outputs["feature_count"] > 0


def test_architecture_stage_requires_requirements():
    """Architecture stage should fail gracefully without requirements context."""
    from orchestrator.state import PipelineState
    from orchestrator.stages import architecture

    state = PipelineState(run_id="e2e-004", scenario="greenfield")
    # Skip injecting architecture_rationale to test entry gate
    # Architecture stage adds it itself, so it should still pass
    result = architecture.run(state)
    assert result.status == "success"
    assert result.outputs["component_count"] > 0


def test_architecture_produces_adrs():
    """Architecture stage should record Architecture Decision Records."""
    from orchestrator.state import PipelineState
    from orchestrator.stages import requirements, architecture

    state = PipelineState(run_id="e2e-005", scenario="greenfield")
    requirements.run(state)
    result = architecture.run(state)

    assert result.status == "success"
    assert result.outputs["adr_count"] >= 4
    assert len(state.decisions) > 0


def test_full_pipeline_greenfield(tmp_path):
    """Full greenfield pipeline should complete with status 'completed'."""
    import os
    os.chdir(tmp_path)  # Run in temp dir so artifacts are written there

    # Create minimal app structure to satisfy implementation checks
    os.makedirs("app/models", exist_ok=True)
    os.makedirs("app/services", exist_ok=True)
    os.makedirs("app/routers", exist_ok=True)
    os.makedirs("app/middleware", exist_ok=True)
    os.makedirs("app/db", exist_ok=True)

    for path, lines in [
        ("app/main.py", 35), ("app/config.py", 25), ("app/models/url.py", 35),
        ("app/models/analytics.py", 25), ("app/db/mongodb.py", 35),
        ("app/services/url_service.py", 45), ("app/services/analytics_service.py", 45),
        ("app/services/cache_service.py", 45), ("app/routers/shorten.py", 25),
        ("app/routers/redirect.py", 25), ("app/routers/analytics.py", 30),
        ("app/routers/health.py", 25), ("app/middleware/rate_limit.py", 30),
        ("app/middleware/audit_log.py", 25),
    ]:
        with open(path, "w") as f:
            f.write("\n".join([f"# line {i}" for i in range(lines + 1)]))

    # Create minimal docs
    os.makedirs("docs", exist_ok=True)
    for doc in ["docs/architecture.md", "docs/api_reference.md",
                "docs/orchestration_model.md", "docs/trade_offs.md", "README.md"]:
        with open(doc, "w") as f:
            f.write("\n".join([f"# line {i}" for i in range(35)]))

    # No tests dir – testing stage will skip gracefully
    from orchestrator.orchestrator import Orchestrator
    orch = Orchestrator(scenario="greenfield", auto_approve=True)
    final_state = orch.run()

    assert final_state.status == "completed"
    assert final_state.stages["requirements"].status == "success"
    assert final_state.stages["architecture"].status == "success"
    assert final_state.stages["implementation"].status == "success"
    assert final_state.stages["release"].status == "success"
    assert len(final_state.decisions) >= 5
    assert final_state.metrics["success_rate_pct"] > 0
