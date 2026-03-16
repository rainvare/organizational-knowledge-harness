"""
Evidence Accumulator — Organizational Knowledge Harness Sprint 2
Collects coherence signals across generation cycles.
Detects patterns and triggers proposal generation when thresholds are met.
"""

from datetime import datetime, timezone
from uuid import uuid4
from core.graph_engine import GraphEngine


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MIN_SIGNALS = 3          # minimum signals before proposing
MIN_CONFIDENCE = 0.75    # average confidence threshold
PROPOSAL_TYPES = {
    "violation": "restrict",     # consistent violations → strengthen restrict node
    "drifting": "update",        # consistent drift → update node detail
    "aligned": None,             # consistent alignment → no proposal needed
}


# ---------------------------------------------------------------------------
# Evidence Accumulator
# ---------------------------------------------------------------------------

class EvidenceAccumulator:
    """
    Accumulates coherence signals across generation cycles.
    When MIN_SIGNALS signals of the same type with avg confidence > MIN_CONFIDENCE
    accumulate for a node, generates a proposal.

    One bad output doesn't change anything. A pattern of 3+ does.
    """

    def __init__(self, graph: GraphEngine):
        self.graph = graph

    def add_signals(self, signals: list[dict]) -> list[dict]:
        """
        Add new signals to the evidence store and check for proposal triggers.

        Returns list of proposals generated (may be empty).
        """
        # Load current evidence from graph state
        evidence = self.graph._evidence

        # Append new signals
        for sig in signals:
            if sig.get("signal_type") not in ("neutral", "aligned"):
                evidence.append(sig)

        # Check triggers
        proposals = self._check_triggers(evidence)

        # Write back
        self.graph._evidence = evidence
        if proposals:
            for p in proposals:
                self.graph._proposals.append(p)
            self.graph.save(
                f"evidence: {len(proposals)} proposal(s) generated"
            )

        return proposals

    def _check_triggers(self, evidence: list[dict]) -> list[dict]:
        """
        Check if any node has accumulated enough evidence to warrant a proposal.
        Returns new proposals that don't already exist in queue.
        """
        # Group signals by (node_id, signal_type)
        groups: dict[tuple, list[dict]] = {}
        for sig in evidence:
            key = (sig["node_id"], sig["signal_type"])
            groups.setdefault(key, []).append(sig)

        # Get existing pending proposals to avoid duplicates
        existing = {
            (p["node_id"], p["proposal_type"])
            for p in self.graph._proposals
            if p.get("status") == "pending"
        }

        proposals = []
        for (node_id, signal_type), sigs in groups.items():
            if len(sigs) < MIN_SIGNALS:
                continue

            avg_confidence = sum(s["confidence"] for s in sigs) / len(sigs)
            if avg_confidence < MIN_CONFIDENCE:
                continue

            proposal_type = PROPOSAL_TYPES.get(signal_type)
            if not proposal_type:
                continue

            if (node_id, proposal_type) in existing:
                continue

            node = self.graph.get_node(node_id)
            if not node:
                continue

            proposal = self._build_proposal(
                node=node,
                signal_type=signal_type,
                proposal_type=proposal_type,
                signals=sigs,
                avg_confidence=avg_confidence,
            )
            proposals.append(proposal)

        return proposals

    def _build_proposal(
        self,
        node: dict,
        signal_type: str,
        proposal_type: str,
        signals: list[dict],
        avg_confidence: float,
    ) -> dict:
        """Build a human-readable proposal for the Proposal Queue."""
        notes = [s["note"] for s in signals if s.get("note")]

        if signal_type == "violation" and node["type"] == "restrict":
            description = (
                f"Node '{node['label']}' has been violated {len(signals)} times "
                f"with avg confidence {avg_confidence:.2f}. "
                f"Consider strengthening or clarifying this constraint."
            )
            suggested_change = {
                "field": "detail",
                "current": node["detail"],
                "suggested": f"{node['detail']} [Needs reinforcement — {len(signals)} violations detected]",
            }
        elif signal_type == "drifting":
            description = (
                f"Node '{node['label']}' shows consistent drift across {len(signals)} cycles "
                f"(avg confidence {avg_confidence:.2f}). "
                f"The current definition may be too vague or misaligned with actual usage."
            )
            suggested_change = {
                "field": "stability",
                "current": node["stability"],
                "suggested": "watch" if node["stability"] == "stable" else node["stability"],
            }
        else:
            description = (
                f"Node '{node['label']}' accumulated {len(signals)} signals "
                f"of type '{signal_type}' with avg confidence {avg_confidence:.2f}."
            )
            suggested_change = None

        return {
            "id": f"prop_{uuid4().hex[:8]}",
            "node_id": node["id"],
            "node_label": node["label"],
            "node_type": node["type"],
            "proposal_type": proposal_type,
            "signal_type": signal_type,
            "signal_count": len(signals),
            "avg_confidence": round(avg_confidence, 3),
            "description": description,
            "suggested_change": suggested_change,
            "evidence_notes": notes[:5],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
        }

    def get_pending(self) -> list[dict]:
        return [p for p in self.graph._proposals if p.get("status") == "pending"]

    def get_all(self) -> list[dict]:
        return self.graph._proposals

    def signal_summary(self) -> dict:
        """Summary of accumulated evidence by node."""
        summary: dict[str, dict] = {}
        for sig in self.graph._evidence:
            nid = sig["node_id"]
            if nid not in summary:
                summary[nid] = {
                    "node_label": sig.get("node_label", nid),
                    "node_type": sig.get("node_type", ""),
                    "total": 0,
                    "by_type": {},
                }
            summary[nid]["total"] += 1
            st = sig["signal_type"]
            summary[nid]["by_type"][st] = summary[nid]["by_type"].get(st, 0) + 1
        return summary
