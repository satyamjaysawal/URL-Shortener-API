"""
scenarios/ambiguous.py – Scenario 3: Handle vague/ambiguous requirements.

Demonstrates:
  - Requirement clarification loop
  - Ambiguity detection and structured Q&A resolution
  - AI-driven normalization of vague requirements
  - Proceeding only after requirements are sufficiently clear
  - Governed escalation when ambiguity cannot be resolved
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Raw ambiguous requirement
RAW_REQUIREMENT = "Make the URL shortener better"

# Simulated clarification Q&A (what an AI agent would ask + receive)
CLARIFICATION_QA = [
    {
        "question": "What does 'better' mean in this context? (performance / features / reliability / UX)",
        "answer": "More features and better reliability",
    },
    {
        "question": "Is there a target user segment? (developers / marketers / general public)",
        "answer": "Developers using the REST API directly",
    },
    {
        "question": "What is the current biggest pain point?",
        "answer": "No way to track how many times a link was clicked, and URLs never expire",
    },
    {
        "question": "Do you have any SLA or latency requirements?",
        "answer": "P95 redirect latency should be under 150ms",
    },
    {
        "question": "Should we support custom branded short codes (aliases)?",
        "answer": "Yes, that would be very useful",
    },
]

# Normalized requirements produced after clarification
NORMALIZED_REQUIREMENTS = [
    "Add click tracking (per-redirect analytics with IP, user-agent, referer)",
    "Add URL expiry via expires_in_hours parameter",
    "Add custom alias support for branded short URLs",
    "Add daily click breakdown endpoint: GET /analytics/detail/{code}",
    "Add top URLs leaderboard: GET /analytics/top",
    "Achieve P95 redirect latency < 150ms (via LRU cache)",
    "Add /health and /metrics endpoints for reliability visibility",
]


def _run_clarification_loop():
    """Simulate the AI clarification loop for ambiguous requirements."""
    print("\n🤔 AMBIGUITY DETECTED – Running Clarification Loop")
    print("─" * 55)
    print(f"  Raw requirement: \"{RAW_REQUIREMENT}\"")
    print("─" * 55)
    print("  Agent is generating clarifying questions...\n")

    for i, qa in enumerate(CLARIFICATION_QA, 1):
        print(f"  Q{i}: {qa['question']}")
        print(f"  A{i}: {qa['answer']}\n")

    print("─" * 55)
    print("  ✅ Ambiguity resolved. Normalized requirements:")
    for req in NORMALIZED_REQUIREMENTS:
        print(f"     • {req}")
    print("─" * 55)


def run(auto_approve: bool = True) -> dict:
    """
    Run the Ambiguous scenario.

    Raw requirement: "Make the URL shortener better"

    Returns pipeline summary dict.
    """
    print("\n" + "=" * 64)
    print("  SCENARIO 3: AMBIGUOUS")
    print(f"  '{RAW_REQUIREMENT}'")
    print("=" * 64)

    _run_clarification_loop()

    orchestrator = Orchestrator(scenario="ambiguous", auto_approve=auto_approve)

    # Inject clarified context so downstream stages know what was resolved
    orchestrator.state.context["raw_requirement"] = RAW_REQUIREMENT
    orchestrator.state.context["clarification_rounds"] = len(CLARIFICATION_QA)
    orchestrator.state.context["normalized_requirements"] = NORMALIZED_REQUIREMENTS

    final_state = orchestrator.run()

    return {
        "scenario": "ambiguous",
        "status": final_state.status,
        "run_id": final_state.run_id,
        "metrics": final_state.metrics,
        "decisions": len(final_state.decisions),
        "clarification_rounds": len(CLARIFICATION_QA),
        "normalized_requirements": len(NORMALIZED_REQUIREMENTS),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    result = run(auto_approve=True)
    print(f"\nScenario result: {result['status'].upper()}")
    print(f"Clarification rounds: {result['clarification_rounds']}")
    print(f"Normalized requirements: {result['normalized_requirements']}")
