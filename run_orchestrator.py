"""
run_orchestrator.py – CLI entry point for the agentic SDLC orchestrator.

Usage:
    python run_orchestrator.py --scenario greenfield
    python run_orchestrator.py --scenario brownfield
    python run_orchestrator.py --scenario ambiguous
    python run_orchestrator.py --scenario all
    python run_orchestrator.py --scenario greenfield --no-auto-approve
"""
import argparse
import logging
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("orchestrator.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Agentic SDLC Orchestrator for URL Shortener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_orchestrator.py --scenario greenfield
  python run_orchestrator.py --scenario brownfield
  python run_orchestrator.py --scenario ambiguous
  python run_orchestrator.py --scenario all
        """,
    )
    parser.add_argument(
        "--scenario",
        choices=["greenfield", "brownfield", "ambiguous", "all"],
        required=True,
        help="Which scenario to run",
    )
    parser.add_argument(
        "--no-auto-approve",
        action="store_true",
        default=False,
        help="Require interactive human approval at release gate",
    )
    args = parser.parse_args()

    auto_approve = not args.no_auto_approve
    scenario = args.scenario

    results = []

    if scenario in ("greenfield", "all"):
        from scenarios.greenfield import run as run_greenfield
        result = run_greenfield(auto_approve=auto_approve)
        results.append(result)

    if scenario in ("brownfield", "all"):
        from scenarios.brownfield import run as run_brownfield
        result = run_brownfield(auto_approve=auto_approve)
        results.append(result)

    if scenario in ("ambiguous", "all"):
        from scenarios.ambiguous import run as run_ambiguous
        result = run_ambiguous(auto_approve=auto_approve)
        results.append(result)

    # Final summary
    print(f"\n{'═'*65}")
    print(f"  ORCHESTRATOR RUN COMPLETE")
    print(f"{'═'*65}")
    for r in results:
        icon = "✅" if r["status"] == "completed" else "❌"
        print(f"  {icon} Scenario: {r['scenario']:<15} Status: {r['status'].upper()}")
        print(f"     Run ID: {r['run_id']}  Decisions: {r['decisions']}")
    print(f"{'═'*65}")
    print(f"\n  Output files:")
    print(f"    audit.jsonl          – Full audit trail (JSON-L)")
    print(f"    pipeline_state.json  – Final pipeline state")
    print(f"    orchestrator.log     – Structured log output")
    print(f"{'═'*65}\n")

    # Exit with error code if any scenario failed
    if any(r["status"] != "completed" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
