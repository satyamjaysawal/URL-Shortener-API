"""
orchestrator/audit.py – Audit log writer in JSON-L format.
Every pipeline action is recorded for full traceability.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = "audit.jsonl"


class AuditLogger:
    """Writes structured JSON-L audit entries to a file."""

    def __init__(self, log_file: str = AUDIT_LOG_FILE):
        self._log_file = log_file
        self._run_id: Optional[str] = None

    def set_run(self, run_id: str):
        self._run_id = run_id

    def log(
        self,
        stage: str,
        action: str,
        outcome: str,
        agent_decision: str = "",
        human_override: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Append a single audit entry to the JSON-L log file."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "stage": stage,
            "action": action,
            "outcome": outcome,
            "agent_decision": agent_decision,
            "human_override": human_override,
            "details": details or {},
        }
        try:
            with open(self._log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except IOError as e:
            logger.warning(f"Failed to write audit log: {e}")

        logger.info(f"[AUDIT] {stage} | {action} | {outcome}")

    def read_all(self) -> list:
        """Return all audit entries for the current run."""
        if not os.path.exists(self._log_file):
            return []
        entries = []
        with open(self._log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if self._run_id is None or entry.get("run_id") == self._run_id:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        pass
        return entries


# Module-level singleton
audit = AuditLogger()
