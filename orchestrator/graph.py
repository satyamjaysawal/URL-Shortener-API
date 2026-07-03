"""
orchestrator/graph.py – Dependency graph and execution scheduler.
Defines the SDLC stage DAG, supports sequential + parallel execution paths.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class StageNode:
    """A node in the pipeline dependency graph."""
    name: str
    depends_on: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None  # Stages sharing a group can run in parallel
    description: str = ""


class DependencyGraph:
    """
    DAG representing SDLC stage dependencies.

    Structure:
        requirements
            └─► architecture
                    └─► implementation
                            ├─► testing        (parallel group A)
                            └─► documentation  (parallel group A)
                                    └─► release
    """

    def __init__(self):
        self._nodes: Dict[str, StageNode] = {}
        self._build_sdlc_dag()

    def _build_sdlc_dag(self):
        stages = [
            StageNode("requirements",   depends_on=[],                description="Parse, clarify, and normalize requirements"),
            StageNode("architecture",   depends_on=["requirements"],  description="Design components, APIs, and data flows"),
            StageNode("implementation", depends_on=["architecture"],  description="Generate and review code artifacts"),
            StageNode("testing",        depends_on=["implementation"], parallel_group="validation", description="Run unit and integration tests"),
            StageNode("documentation",  depends_on=["implementation"], parallel_group="validation", description="Generate API and architecture docs"),
            StageNode("release",        depends_on=["testing", "documentation"], description="Release readiness gate with human approval"),
        ]
        for s in stages:
            self._nodes[s.name] = s

    def add_stage(self, node: StageNode):
        self._nodes[node.name] = node

    def get_execution_order(self) -> List[List[str]]:
        """
        Topological sort returning batches of stages that can run in parallel.
        Each inner list is a batch; batches must run sequentially.
        """
        in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
        for node in self._nodes.values():
            for dep in node.depends_on:
                in_degree[node.name] += 1

        batches: List[List[str]] = []
        completed: Set[str] = set()

        while len(completed) < len(self._nodes):
            # Find all stages with all dependencies satisfied
            ready = [
                name for name, node in self._nodes.items()
                if name not in completed
                and all(dep in completed for dep in node.depends_on)
            ]
            if not ready:
                raise RuntimeError("Dependency graph has a cycle!")
            batches.append(sorted(ready))
            completed.update(ready)

        return batches

    def get_dependencies(self, stage: str) -> List[str]:
        return self._nodes[stage].depends_on if stage in self._nodes else []

    def describe(self) -> str:
        lines = ["📊 SDLC Dependency Graph:"]
        for batch_idx, batch in enumerate(self.get_execution_order()):
            parallel = " ‖ ".join(batch)
            lines.append(f"  Batch {batch_idx + 1}: [{parallel}]")
        return "\n".join(lines)
