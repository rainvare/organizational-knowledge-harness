"""
core/graph_engine.py
Typed knowledge graph with NM_graph stability metric and git-native versioning.
"""
import json
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional


VALID_TYPES = {"brand", "audience", "value", "tone", "restrict", "example", "color", "typography", "visual"}
VALID_STABILITY = {"stable", "watch", "flagged"}


class GraphEngine:
    """
    Core knowledge graph engine.
    
    Node structure:
      { id, type, label, detail, source, stability, created_at, updated_at }
    
    Edge structure:
      { id, from, to, relation, weight, created_at }
    
    NM_graph metric (adapted from Muñoz Number, UFAL DOI:10.5281/zenodo.18653104):
      F = flagged_nodes / total_nodes
      C = control_edges / total_edges
      NM = C - F  ∈ [-1, 1]
      
      States:
        NM >= 0.5  → stable
        NM >= 0.0  → watch
        NM ≈ 0     → bifurcation  (|NM| < 0.05)
        NM < 0     → unstable
        no data    → insufficient_data
    """

    def __init__(self, path: str = "data/graph_state.json"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._nodes: dict = {}
        self._edges: list = []
        self._evidence: list = []
        self._proposals: list = []
        self._load()

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load(self):
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._nodes = data.get("nodes", {})
                self._edges = data.get("edges", [])
                self._evidence = data.get("evidence", [])
                self._proposals = data.get("proposals", [])
            except Exception:
                pass

    def _to_dict(self) -> dict:
        return {
            "nodes": self._nodes,
            "edges": self._edges,
            "evidence": self._evidence,
            "proposals": self._proposals,
            "meta": {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "nm_graph": self.nm_graph(),
            },
        }

    def save(self, commit_message: str = "update"):
        self._path.write_text(
            json.dumps(self._to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._git_commit(commit_message)

    def _git_commit(self, message: str):
        try:
            repo_root = self._path.parent.parent
            subprocess.run(
                ["git", "add", str(self._path)],
                cwd=repo_root, capture_output=True, timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", f"harness: {message}"],
                cwd=repo_root, capture_output=True, timeout=10
            )
        except Exception:
            pass  # Git not available in all environments

    def history(self) -> list:
        try:
            repo_root = self._path.parent.parent
            result = subprocess.run(
                ["git", "log", "--oneline", "-20", str(self._path)],
                cwd=repo_root, capture_output=True, text=True, timeout=10
            )
            commits = []
            for line in result.stdout.strip().splitlines():
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    commits.append({"hash": parts[0], "message": parts[1]})
            return commits
        except Exception:
            return []

    def rollback(self, commit_hash: str):
        try:
            repo_root = self._path.parent.parent
            subprocess.run(
                ["git", "checkout", commit_hash, "--", str(self._path)],
                cwd=repo_root, capture_output=True, timeout=10
            )
            self._load()
        except Exception as e:
            raise RuntimeError(f"Rollback failed: {e}")

    # ── Nodes ──────────────────────────────────────────────────────────────────

    def add_node(
        self,
        node_type: str,
        label: str,
        detail: str,
        source: str = "manual",
        stability: str = "stable",
    ) -> str:
        if node_type not in VALID_TYPES:
            raise ValueError(f"Invalid type '{node_type}'. Must be one of {VALID_TYPES}")
        if stability not in VALID_STABILITY:
            stability = "stable"

        # Deduplicate by label + type
        for nid, n in self._nodes.items():
            if n["type"] == node_type and n["label"].lower() == label.lower():
                # Update detail if richer
                if len(detail) > len(n["detail"]):
                    self._nodes[nid]["detail"] = detail
                    self._nodes[nid]["updated_at"] = datetime.utcnow().isoformat()
                return nid

        nid = str(uuid.uuid4())[:8]
        self._nodes[nid] = {
            "id": nid,
            "type": node_type,
            "label": label,
            "detail": detail,
            "source": source,
            "stability": stability,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        return nid

    def get_node(self, node_id: str) -> Optional[dict]:
        return self._nodes.get(node_id)

    def get_nodes(
        self,
        node_type: Optional[str] = None,
        stability: Optional[str] = None,
    ) -> list:
        nodes = list(self._nodes.values())
        if node_type:
            nodes = [n for n in nodes if n["type"] == node_type]
        if stability:
            nodes = [n for n in nodes if n["stability"] == stability]
        return nodes

    def update_node(self, node_id: str, **kwargs):
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} not found")
        for k, v in kwargs.items():
            if k in ("detail", "label", "stability", "source"):
                self._nodes[node_id][k] = v
        self._nodes[node_id]["updated_at"] = datetime.utcnow().isoformat()

    def flag_node(self, node_id: str):
        self.update_node(node_id, stability="flagged")

    # ── Edges ──────────────────────────────────────────────────────────────────

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        weight: float = 1.0,
        is_control: bool = False,
    ) -> str:
        # Deduplicate
        for e in self._edges:
            if e["from"] == from_id and e["to"] == to_id and e["relation"] == relation:
                return e["id"]

        eid = str(uuid.uuid4())[:8]
        self._edges.append({
            "id": eid,
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "weight": weight,
            "is_control": is_control,
            "created_at": datetime.utcnow().isoformat(),
        })
        return eid

    def get_edges(
        self,
        from_id: Optional[str] = None,
        to_id: Optional[str] = None,
    ) -> list:
        edges = self._edges
        if from_id:
            edges = [e for e in edges if e["from"] == from_id]
        if to_id:
            edges = [e for e in edges if e["to"] == to_id]
        return edges

    # ── NM_graph ───────────────────────────────────────────────────────────────

    def nm_graph(self) -> dict:
        total_nodes = len(self._nodes)
        total_edges = len(self._edges)

        if total_nodes == 0:
            return {
                "nm": None,
                "state": "insufficient_data",
                "f": None,
                "c": None,
                "flagged_nodes": 0,
                "total_nodes": 0,
                "control_edges": 0,
                "total_edges": 0,
            }

        flagged_nodes = sum(
            1 for n in self._nodes.values() if n.get("stability") == "flagged"
        )
        control_edges = sum(1 for e in self._edges if e.get("is_control", False))

        F = flagged_nodes / total_nodes if total_nodes > 0 else 0
        C = control_edges / total_edges if total_edges > 0 else 0
        nm = round(C - F, 4)

        if abs(nm) < 0.05:
            state = "bifurcation"
        elif nm >= 0.5:
            state = "stable"
        elif nm >= 0.0:
            state = "watch"
        else:
            state = "unstable"

        return {
            "nm": nm,
            "state": state,
            "f": round(F, 4),
            "c": round(C, 4),
            "flagged_nodes": flagged_nodes,
            "total_nodes": total_nodes,
            "control_edges": control_edges,
            "total_edges": total_edges,
        }

    # ── Summary ────────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        nodes_by_type: dict = {}
        for n in self._nodes.values():
            nodes_by_type[n["type"]] = nodes_by_type.get(n["type"], 0) + 1
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": nodes_by_type,
            "nm_graph": self.nm_graph(),
        }
