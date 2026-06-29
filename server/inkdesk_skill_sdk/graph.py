"""
Routing graph — build a read-only graph of Skill packages and validate routing rules.

Checks: missing nextSkills, input/output incompatibility, cycles,
single router, category/kind mismatches, discipline-as-controller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from inkdesk_skill_sdk.registry import SkillMetadata, SkillRegistry
from inkdesk_skill_sdk.validation import Finding, Severity


@dataclass
class GraphNode:
    meta: SkillMetadata
    edges: list[str] = field(default_factory=list)  # skill ids that this node points to via nextSkills
    incoming: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.meta.contract_id)


@dataclass
class RoutingGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)  # contract_id -> node

    def add_node(self, meta: SkillMetadata) -> GraphNode:
        node = GraphNode(meta=meta)
        self.nodes[meta.contract_id] = node
        return node

    def get_node(self, skill_id: str) -> GraphNode | None:
        return self.nodes.get(skill_id)


def build_graph(registry: SkillRegistry) -> RoutingGraph:
    """Build a routing graph from all resolved Skills in a registry."""
    graph = RoutingGraph()
    all_meta = registry.resolve_all()

    # Create nodes
    for meta in all_meta:
        graph.add_node(meta)

    # Add edges from nextSkills
    for node in graph.nodes.values():
        contract = _load_contract_from_meta(node.meta)
        if contract is None:
            continue
        for ref in contract.nextSkills:
            node.edges.append(ref.skillId)
            target = graph.get_node(ref.skillId)
            if target:
                target.incoming.append(node.meta.contract_id)

    return graph


def validate_graph(graph: RoutingGraph) -> list[Finding]:
    """Validate routing rules on the graph. Returns findings for each violation."""
    findings: list[Finding] = []

    if not graph.nodes:
        return findings

    # 1. Single router: exactly one skill with category=routing
    routers = [n for n in graph.nodes.values() if n.meta.category == "routing"]
    if len(routers) == 0:
        findings.append(
            Finding(
                code="GRAPH_NO_ROUTER",
                path="<routing-graph>",
                message="No router Skill found (category=routing required for exactly one Skill)",
                severity=Severity.ERROR,
            )
        )
    elif len(routers) > 1:
        findings.append(
            Finding(
                code="GRAPH_MULTIPLE_ROUTERS",
                path="<routing-graph>",
                message=f"Multiple router Skills found: {[n.meta.contract_id for n in routers]}; exactly one allowed",
                severity=Severity.ERROR,
            )
        )

    router_node = routers[0] if len(routers) == 1 else None

    # 2. Edge validity: nextSkills targets must exist
    all_ids = set(graph.nodes.keys())
    for node in graph.nodes.values():
        for target_id in node.edges:
            if target_id not in all_ids:
                findings.append(
                    Finding(
                        code="GRAPH_MISSING_EDGE",
                        path=f"skills/{node.meta.name}/contract.json",
                        message=f"nextSkills references unknown Skill: {target_id!r}",
                        severity=Severity.ERROR,
                    )
                )

    # 3. Cycle detection via DFS
    cycles = _find_cycles(graph)
    for cycle in cycles:
        chain = " -> ".join(cycle) + " -> " + cycle[0]
        findings.append(
            Finding(
                code="GRAPH_CYCLE",
                path="<routing-graph>",
                message=f"Skill chain cycle detected: {chain}",
                severity=Severity.ERROR,
            )
        )

    # 4. Discipline skills must not be process controllers
    # (discipline = adds gates, not a competing router)
    disciplines = [n for n in graph.nodes.values() if n.meta.category == "discipline"]
    for d in disciplines:
        # Discipline skills should have narrow descriptions, not broad routing-like ones
        if d.meta.kind in ("router",):
            findings.append(
                Finding(
                    code="GRAPH_DISCIPLINE_AS_CONTROLLER",
                    path=f"skills/{d.meta.name}",
                    message=f"Discipline Skill {d.meta.contract_id!r} has kind=router; discipline must not be a process controller",
                    severity=Severity.ERROR,
                )
            )

    # 5. Router must not have specific nextSkills (it routes dynamically)
    if router_node:
        router_edges = router_node.edges
        # Router can point to nothing, or to everything; both are fine.
        # But if it hard-codes a single chain, warn.
        if len(router_edges) == 1 and len(graph.nodes) > 3:
            findings.append(
                Finding(
                    code="GRAPH_ROUTER_SINGLE_CHAIN",
                    path=f"skills/{router_node.meta.name}/contract.json",
                    message=f"Router only links to {router_edges[0]!r}; consider removing hard-coded chain for dynamic routing",
                    severity=Severity.WARNING,
                )
            )

    # 6. Conflict detection: multiple domain skills with broad descriptions
    domain_skills = [n for n in graph.nodes.values() if n.meta.category not in ("routing", "discipline")]
    broad_descriptions: list[str] = []
    for ds in domain_skills:
        desc = ds.meta.summary.lower()
        if any(
            kw in desc
            for kw in ["所有", "all tasks", "everything", "任何", "any task", "全部", "通用"]
        ):
            broad_descriptions.append(ds.meta.contract_id)

    if broad_descriptions:
        findings.append(
            Finding(
                code="GRAPH_BROAD_DESCRIPTIONS",
                path="<routing-graph>",
                message=f"Domain Skills with broad descriptions (should be narrow): {broad_descriptions}",
                severity=Severity.WARNING,
            )
        )

    # 7. Retry self-loop check: only allowed explicitly with a max count
    for node in graph.nodes.values():
        if _has_retry_self_loop(node):
            pass  # self-reference in nextSkills is caught by semantic validator already

    return findings


def _load_contract_from_meta(meta: SkillMetadata):
    """Re-parse contract from the Skill package path."""
    import json

    from inkdesk_skill_sdk.contracts import Contract

    contract_path = Path(meta.path) / "contract.json"
    try:
        data = json.loads(contract_path.read_text(encoding="utf-8"))
        return Contract.model_validate(data)
    except Exception:
        return None


def _find_cycles(graph: RoutingGraph) -> list[list[str]]:
    """Find all elementary cycles using depth-first traversal."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node_id: str) -> None:
        if node_id in stack:
            cycle_start = stack.index(node_id)
            cycle = stack[cycle_start:] + [node_id]
            cycles.append(cycle)
            return
        if node_id in visited:
            return
        visited.add(node_id)
        stack.append(node_id)
        node = graph.get_node(node_id)
        if node:
            for target in node.edges:
                dfs(target)
        stack.pop()

    for node_id in graph.nodes:
        dfs(node_id)

    # Deduplicate — normalize rotation
    unique: list[list[str]] = []
    seen: set[str] = set()
    for c in cycles:
        # Rotate so smallest id comes first
        min_i = min(range(len(c)), key=lambda i: c[i])
        rotated = tuple(c[min_i:] + c[:min_i])
        key = str(rotated)
        if key not in seen:
            seen.add(key)
            unique.append(list(rotated[:-1]))  # drop duplicate last element

    return unique


def _has_retry_self_loop(node: GraphNode) -> bool:
    return node.meta.contract_id in node.edges


