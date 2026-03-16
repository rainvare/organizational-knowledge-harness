"""
Graph Engine — Organizational Knowledge Harness
Core data layer: CRUD, persistence, git versioning, NM_graph stability metric.
"""

import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NODE_TYPES = {"brand", "audience", "value", "tone", "restrict", "example"}
EDGE_RELATIONS = {
    "targets", "reaches", "embodies", "shapes",
    "constrains", "constrained_by", "exemplified_by", "validates", "limits"
}
CONTROL_EDGES = {"validates", "limits", "constrains", "constrained_by"}
STABILITY_STATES = {"stable", "watch", "flagged"}
NM_MAX = 3.0   # clamp when F = 0 (no flagged nodes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp_pos(x: float, eps: float = 1e-9) -> float:
    return x if x > eps else eps


# ---------------------------------------------------------------------------
# Graph Engine
# ---------------------------------------------------------------------------

class GraphEngine:
    """
    Knowledge graph with typed nodes, semantic edges, JSON persistence,
    git-based versioning, and NM_graph stability metric.
    """

    def __init__(self, data_path: str = "data/graph_state.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        self._nodes: dict[str, dict] = {}
        self._edges: list[dict] = []
        self._evidence: list[dict] = []
        self._proposals: list[dict] = []

        if self.data_path.exists():
            self.load()

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def load(self):
        """Load graph state from JSON."""
        with open(self.data_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self._nodes = {n["id"]: n for n in state.get("nodes", [])}
        self._edges = state.get("edges", [])
        self._evidence = state.get("evidence", [])
        self._proposals = state.get("proposals", [])

    def save(self, commit_message: str = "update graph state"):
        """Persist graph state to JSON and commit to git."""
        state = {
            "updated_at": _now(),
            "nodes": list(self._nodes.values()),
            "edges": self._edges,
            "evidence": self._evidence,
            "proposals": self._proposals,
        }
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        self._git_commit(commit_message)

    def _git_commit(self, message: str):
        """Stage graph_state.json and commit if inside a git repo."""
        try:
            repo_root = self.data_path.parent.parent
            subprocess.run(
                ["git", "add", str(self.data_path)],
                cwd=repo_root, check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_root, check=True,
                capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Not a git repo or git not available — fail silently
            pass

    # -----------------------------------------------------------------------
    # Node CRUD
    # -----------------------------------------------------------------------

    def add_node(
        self,
        node_type: str,
        label: str,
        detail: str,
        source: str = "",
        weight: float = 1.0,
        stability: str = "stable",
        node_id: Optional[str] = None,
    ) -> dict:
        if node_type not in NODE_TYPES:
            raise ValueError(f"Invalid node type: {node_type}. Must be one of {NODE_TYPES}")
        if stability not in STABILITY_STATES:
            raise ValueError(f"Invalid stability: {stability}")

        node = {
            "id": node_id or f"{node_type[:3]}_{uuid4().hex[:6]}",
            "type": node_type,
            "label": label,
            "detail": detail,
            "weight": weight,
            "stability": stability,
            "source": source,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self._nodes[node["id"]] = node
        return node

    def get_node(self, node_id: str) -> Optional[dict]:
        return self._nodes.get(node_id)

    def get_nodes(self, node_type: Optional[str] = None, stability: Optional[str] = None) -> list[dict]:
        nodes = list(self._nodes.values())
        if node_type:
            nodes = [n for n in nodes if n["type"] == node_type]
        if stability:
            nodes = [n for n in nodes if n["stability"] == stability]
        return nodes

    def update_node(self, node_id: str, changes: dict) -> dict:
        if node_id not in self._nodes:
            raise KeyError(f"Node not found: {node_id}")
        protected = {"id", "created_at"}
        for k, v in changes.items():
            if k not in protected:
                self._nodes[node_id][k] = v
        self._nodes[node_id]["updated_at"] = _now()
        return self._nodes[node_id]

    def delete_node(self, node_id: str):
        if node_id not in self._nodes:
            raise KeyError(f"Node not found: {node_id}")
        del self._nodes[node_id]
        self._edges = [
            e for e in self._edges
            if e["from"] != node_id and e["to"] != node_id
        ]

    # -----------------------------------------------------------------------
    # Edge CRUD
    # -----------------------------------------------------------------------

    def add_edge(self, from_id: str, to_id: str, relation: str, weight: float = 1.0) -> dict:
        if relation not in EDGE_RELATIONS:
            raise ValueError(f"Invalid relation: {relation}. Must be one of {EDGE_RELATIONS}")
        if from_id not in self._nodes:
            raise KeyError(f"Source node not found: {from_id}")
        if to_id not in self._nodes:
            raise KeyError(f"Target node not found: {to_id}")

        edge = {
            "id": f"edge_{uuid4().hex[:8]}",
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "weight": weight,
            "created_at": _now(),
        }
        self._edges.append(edge)
        return edge

    def get_edges(self, from_id: Optional[str] = None, relation: Optional[str] = None) -> list[dict]:
        edges = self._edges
        if from_id:
            edges = [e for e in edges if e["from"] == from_id]
        if relation:
            edges = [e for e in edges if e["relation"] == relation]
        return edges

    def delete_edge(self, edge_id: str):
        self._edges = [e for e in self._edges if e["id"] != edge_id]

    # -----------------------------------------------------------------------
    # Graph traversal (used by Generation Agent)
    # -----------------------------------------------------------------------

    def query_nodes(self, node_type: Optional[str] = None, stability: Optional[str] = None) -> list[dict]:
        return self.get_nodes(node_type=node_type, stability=stability)

    def query_edges(self, from_id: str, relation: Optional[str] = None) -> list[dict]:
        return self.get_edges(from_id=from_id, relation=relation)

    def get_constraints(self) -> list[dict]:
        """Return all restrict nodes — hard constraints for generation."""
        return self.get_nodes(node_type="restrict")

    def get_examples(self, linked_to: Optional[str] = None) -> list[dict]:
        """Return example nodes, optionally filtered by linked node."""
        examples = self.get_nodes(node_type="example")
        if not linked_to:
            return examples
        linked_ids = {e["from"] for e in self._edges if e["to"] == linked_to}
        linked_ids |= {e["to"] for e in self._edges if e["from"] == linked_to}
        return [e for e in examples if e["id"] in linked_ids]

    def get_neighborhood(self, node_id: str, depth: int = 1) -> dict:
        """Return node and its immediate neighbors up to given depth."""
        visited = {node_id}
        frontier = {node_id}
        result_nodes = []
        result_edges = []

        for _ in range(depth):
            next_frontier = set()
            for nid in frontier:
                node = self._nodes.get(nid)
                if node:
                    result_nodes.append(node)
                edges = [
                    e for e in self._edges
                    if e["from"] == nid or e["to"] == nid
                ]
                for e in edges:
                    result_edges.append(e)
                    neighbor = e["to"] if e["from"] == nid else e["from"]
                    if neighbor not in visited:
                        next_frontier.add(neighbor)
                        visited.add(neighbor)
            frontier = next_frontier

        return {"nodes": result_nodes, "edges": result_edges}

    # -----------------------------------------------------------------------
    # NM_graph — stability metric
    # -----------------------------------------------------------------------

    def nm_graph(self) -> dict:
        """
        Compute graph stability score adapted from the Muñoz Number (UFAL).

        F (drive)       = flagged_nodes / total_nodes
        C (conductance) = control_edges / total_edges
        NM_graph        = -ln(F / C)

        NM > 0.5 → stable
        NM 0–0.5 → watch
        NM ≈ 0   → bifurcation
        NM < 0   → unstable

        Reference: Muñoz Rodríguez (2026), DOI: 10.5281/zenodo.18653104
        Adaptation: graph-level proxies, not attention-based measurements.
        """
        total_nodes = len(self._nodes)
        total_edges = len(self._edges)

        if total_nodes < 5 or total_edges < 3:
            return {
                "nm": None,
                "state": "insufficient_data",
                "f": None,
                "c": None,
                "flagged_nodes": 0,
                "control_edges": 0,
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "message": "Graph too small for reliable metric (min 5 nodes, 3 edges)",
            }

        flagged = sum(1 for n in self._nodes.values() if n["stability"] == "flagged")
        control = sum(1 for e in self._edges if e["relation"] in CONTROL_EDGES)

        f = flagged / total_nodes
        c = control / total_edges

        if f == 0:
            nm = NM_MAX
        elif c == 0:
            nm = float("-inf")
        else:
            nm = -math.log(_clamp_pos(f) / _clamp_pos(c))

        if nm == float("-inf") or nm < 0:
            state = "unstable"
        elif nm < 0.1:
            state = "bifurcation"
        elif nm < 0.5:
            state = "watch"
        else:
            state = "stable"

        return {
            "nm": round(nm, 4) if nm != float("-inf") else nm,
            "state": state,
            "f": round(f, 4),
            "c": round(c, 4),
            "flagged_nodes": flagged,
            "control_edges": control,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
        }

    # -----------------------------------------------------------------------
    # Git history
    # -----------------------------------------------------------------------

    def history(self, n: int = 20) -> list[dict]:
        """Return last n git commits for graph_state.json."""
        try:
            repo_root = self.data_path.parent.parent
            result = subprocess.run(
                ["git", "log", f"-{n}", "--oneline", "--follow",
                 "--", str(self.data_path)],
                cwd=repo_root, capture_output=True, text=True, check=True
            )
            lines = result.stdout.strip().split("\n")
            commits = []
            for line in lines:
                if line.strip():
                    parts = line.split(" ", 1)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else ""
                    })
            return commits
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def rollback(self, commit_hash: str):
        """Restore graph_state.json to a previous commit and reload."""
        try:
            repo_root = self.data_path.parent.parent
            subprocess.run(
                ["git", "checkout", commit_hash, "--", str(self.data_path)],
                cwd=repo_root, check=True, capture_output=True
            )
            self.load()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Rollback failed: {e.stderr.decode()}") from e

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    def summary(self) -> dict:
        type_counts = {}
        for n in self._nodes.values():
            type_counts[n["type"]] = type_counts.get(n["type"], 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": type_counts,
            "pending_proposals": sum(1 for p in self._proposals if p.get("status") == "pending"),
            "nm_graph": self.nm_graph(),
        }
