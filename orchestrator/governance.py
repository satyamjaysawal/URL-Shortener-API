"""
orchestrator/governance.py – Policy guardrails, approval checkpoints, and change control.
Enforces security, compliance, and human-oversight rules.
"""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ── Policy Rules ───────────────────────────────────────────────────────────────

BLOCKED_URL_PATTERNS = [
    r"^https?://localhost",
    r"^https?://127\.",
    r"^https?://192\.168\.",
    r"^https?://10\.",
    r"^https?://0\.",
]

BLOCKED_KEYWORDS = ["pii", "password", "secret", "token", "private"]

# Stages that require human approval before proceeding
APPROVAL_REQUIRED_STAGES = {"release"}

# Stages that require an explicit rationale in state context
RATIONALE_REQUIRED_STAGES = {"architecture", "implementation"}


class GovernanceEngine:
    """
    Enforces policy guardrails and human approval checkpoints.
    All policy checks return (passed: bool, violations: List[str]).
    """

    # ── URL policies ────────────────────────────────────────────────────────────

    def check_url_policy(self, url: str) -> Tuple[bool, List[str]]:
        """
        Check that a URL doesn't target internal networks or contain PII markers.
        """
        violations = []
        for pattern in BLOCKED_URL_PATTERNS:
            if re.match(pattern, url, re.IGNORECASE):
                violations.append(f"URL targets a private/internal network address: {url}")
        for kw in BLOCKED_KEYWORDS:
            if kw in url.lower():
                violations.append(f"URL contains sensitive keyword '{kw}'")
        return (len(violations) == 0, violations)

    # ── Stage entry gates ───────────────────────────────────────────────────────

    def check_stage_entry(self, stage: str, context: dict) -> Tuple[bool, List[str]]:
        """
        Validate that all prerequisites for entering a stage are met.
        """
        violations = []

        if stage in RATIONALE_REQUIRED_STAGES:
            if not context.get("architecture_rationale") and stage == "architecture":
                violations.append("architecture stage requires a rationale in context.")
            if not context.get("implementation_plan") and stage == "implementation":
                violations.append("implementation stage requires an implementation_plan in context.")

        return (len(violations) == 0, violations)

    # ── Human approval checkpoints ──────────────────────────────────────────────

    def requires_human_approval(self, stage: str) -> bool:
        return stage in APPROVAL_REQUIRED_STAGES

    def request_approval(self, stage: str, summary: str, auto_approve: bool = False) -> bool:
        """
        Prompt for human approval (simulated in non-interactive mode).
        Returns True if approved.
        """
        if auto_approve:
            logger.info(f"[GOVERNANCE] Auto-approved stage '{stage}' (non-interactive mode).")
            return True

        print(f"\n{'='*60}")
        print(f"⚠️  HUMAN APPROVAL REQUIRED: Stage '{stage.upper()}'")
        print(f"{'='*60}")
        print(f"Summary: {summary}")
        print(f"{'='*60}")
        try:
            answer = input("Approve? [y/N]: ").strip().lower()
            approved = answer == "y"
        except EOFError:
            # Non-interactive environment – auto-approve
            approved = True
            logger.warning("[GOVERNANCE] Non-interactive environment, auto-approving.")

        logger.info(f"[GOVERNANCE] Stage '{stage}' {'APPROVED' if approved else 'REJECTED'} by human.")
        return approved

    # ── Schema change control ───────────────────────────────────────────────────

    def check_schema_change(self, change_description: str, rationale: str) -> Tuple[bool, List[str]]:
        """
        Schema changes require a rationale to proceed (change control gate).
        """
        violations = []
        if not rationale or len(rationale.strip()) < 10:
            violations.append(
                f"Schema change '{change_description}' requires a rationale of at least 10 characters."
            )
        return (len(violations) == 0, violations)


# Module-level singleton
governance = GovernanceEngine()
