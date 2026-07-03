"""
scenarios/greenfield.py – Scenario 1: Build a URL shortener from scratch.

Demonstrates:
  - Full SDLC decomposition from a new requirement
  - Complete DAG traversal (requirements → architecture → implementation → testing+docs → release)
  - Greenfield architecture decisions and code generation
  - Full audit trail and metrics
"""
import logging
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def run(auto_approve: bool = True) -> dict:
    """
    Run the Greenfield scenario.

    Requirement: "Build a URL shortener service from scratch with core APIs,
    analytics, and reliability features."

    Returns pipeline summary dict.
    """
    print("\n" + "=" * 64)
    print("  SCENARIO 1: GREENFIELD")
    print("  'Build a URL shortener from scratch'")
    print("=" * 64)

    orchestrator = Orchestrator(scenario="greenfield", auto_approve=auto_approve)
    final_state = orchestrator.run()

    return {
        "scenario": "greenfield",
        "status": final_state.status,
        "run_id": final_state.run_id,
        "metrics": final_state.metrics,
        "decisions": len(final_state.decisions),
    }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    result = run(auto_approve=True)
    print(f"\nScenario result: {result['status'].upper()}")
