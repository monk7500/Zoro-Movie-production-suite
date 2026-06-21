"""
DataDependencyIndex – maps Bible paths to agents that depend on them.
"""

import networkx as nx
from typing import Dict, Set


class DataDependencyIndex:
    def __init__(self, registry: dict, graph: nx.DiGraph):
        self.graph = graph
        self.path_to_agents: Dict[str, Set[str]] = {}
        for agent_name, spec in registry.items():
            for slice_name, path_expr in spec.get("input_spec", {}).items():
                self.path_to_agents.setdefault(path_expr, set()).add(agent_name)

    def affected_agents(self, changed_path: str) -> Set[str]:
        direct = set()
        for prefix, agents in self.path_to_agents.items():
            if changed_path == prefix or changed_path.startswith(prefix + "."):
                direct.update(agents)
        closure = set(direct)
        for agent in direct:
            closure.update(nx.descendants(self.graph, agent))
        return closure
