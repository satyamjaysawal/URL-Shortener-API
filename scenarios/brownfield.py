"""
scenarios/brownfield.py – Scenario 2: Enhance existing URL shortener.

Demonstrates:
  - Brownfield codebase reasoning: identifies impacted modules
  - Incremental feature addition: URL expiry + detailed analytics
  - Impact analysis before implementation
  - Schema change control gate
  - Backward compatibility validation
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.orchestrator import Orchestrator
from orchestrator.state import PipelineState

logger = logging.getLogger(__name__)

# Impacted modules analysis for brownfield
IMPACTED_MODULES = {
    "app/models/url.py": {
        "reason": "Add 'expires_at' and 'custom_alias' fields",
        "risk": "low – new nullable fields, backward compatible",
        "change_type": "additive",
    },
    "app/services/url_service.py": {
        "reason": "Add expiry check in resolve_url(); support custom alias in create_short_url()",
        "risk": "medium – logic change in hot path",
        "change_type": "modified",
    },
    "app/routers/analytics.py": {
        "reason": "Add /detail/{code} and /top endpoints",
        "risk": "low – additive new endpoints",
        "change_type": "additive",
    },
    "app/services/analytics_service.py": {
        "reason": "New service – click recording and aggregation",
        "risk": "low – new file",
        "change_type": "new",
    },
    "app/routers/redirect.py": {
        "reason": "Add click event recording on redirect",
        "risk": "low – additive side-effect call",
        "change_type": "modified",
    },
}


def _print_impact_analysis():
    print("\n📊 BROWNFIELD IMPACT ANALYSIS")
    print("─" * 55)
    for module, info in IMPACTED_MODULES.items():
        risk_icon = "🟡" if info["risk"].startswith("medium") else "🟢"
        print(f"  {risk_icon} {module}")
        print(f"     Reason     : {info['reason']}")
        print(f"     Risk       : {info['risk']}")
        print(f"     Change type: {info['change_type']}")
    print("─" * 55)


def run(auto_approve: bool = True) -> dict:
    """
    Run the Brownfield scenario.

    Requirement: "Add URL expiry and detailed analytics to the existing URL shortener.
    Ensure backward compatibility with existing short URLs."

    Returns pipeline summary dict.
    """
    print("\n" + "=" * 64)
    print("  SCENARIO 2: BROWNFIELD")
    print("  'Add expiry + analytics to existing URL shortener'")
    print("=" * 64)

    _print_impact_analysis()

    orchestrator = Orchestrator(scenario="brownfield", auto_approve=auto_approve)

    # Inject brownfield context: existing modules identified
    orchestrator.state.context["existing_modules"] = list(IMPACTED_MODULES.keys())
    orchestrator.state.context["backward_compat_required"] = True
    orchestrator.state.context["impacted_modules"] = IMPACTED_MODULES

    final_state = orchestrator.run()

    return {
        "scenario": "brownfield",
        "status": final_state.status,
        "run_id": final_state.run_id,
        "metrics": final_state.metrics,
        "decisions": len(final_state.decisions),
        "impacted_modules": len(IMPACTED_MODULES),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    result = run(auto_approve=True)
    print(f"\nScenario result: {result['status'].upper()}")
    print(f"Impacted modules: {result['impacted_modules']}")
