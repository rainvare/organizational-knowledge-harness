"""
Context Exporter — Organizational Knowledge Harness Sprint 4
Exports the knowledge graph in multiple formats for use outside the system.
Formats: JSON, Markdown, Plain text prompt, CSV
"""

import csv
import io
import json
from datetime import datetime, timezone
from core.graph_engine import GraphEngine


class ContextExporter:
    """Exports graph state in formats consumable by external tools and AIs."""

    def __init__(self, graph: GraphEngine):
        self.graph = graph

    # -----------------------------------------------------------------------
    # JSON — machine-readable full export
    # -----------------------------------------------------------------------

    def to_json(self, include_evidence: bool = False) -> str:
        nodes = self.graph.get_nodes()
        edges = self.graph.get_edges()
        nm = self.graph.nm_graph()

        export = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "nm_graph": nm,
            "nodes": nodes,
            "edges": edges,
        }
        if include_evidence:
            export["evidence"] = self.graph._evidence
            export["proposals"] = self.graph._proposals

        return json.dumps(export, indent=2, ensure_ascii=False)

    # -----------------------------------------------------------------------
    # Markdown — human-readable structured document
    # -----------------------------------------------------------------------

    def to_markdown(self) -> str:
        lines = []
        lines.append("# Organizational Knowledge Graph")
        lines.append(f"*Exported {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
        lines.append("")

        nm = self.graph.nm_graph()
        if nm.get("nm") is not None:
            lines.append(f"> **NM_graph stability:** {nm['nm']:.3f} — {nm['state'].upper()}")
            lines.append("")

        sections = {
            "restrict": "## Hard Constraints",
            "value": "## Core Values",
            "brand": "## Brand Identity",
            "audience": "## Target Audiences",
            "tone": "## Tone & Voice",
            "example": "## Examples",
        }

        for node_type, heading in sections.items():
            nodes = self.graph.get_nodes(node_type=node_type)
            if not nodes:
                continue
            lines.append(heading)
            for n in nodes:
                stability_note = f" *({n['stability']})*" if n["stability"] != "stable" else ""
                lines.append(f"### {n['label']}{stability_note}")
                lines.append(n["detail"])
                edges_out = self.graph.get_edges(from_id=n["id"])
                if edges_out:
                    rels = []
                    for e in edges_out:
                        tgt = self.graph.get_node(e["to"])
                        if tgt:
                            rels.append(f"`{e['relation']}` → {tgt['label']}")
                    if rels:
                        lines.append(f"*Relations: {', '.join(rels)}*")
                lines.append("")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Plain text prompt — ready to paste into any AI
    # -----------------------------------------------------------------------

    def to_prompt(self) -> str:
        lines = []
        lines.append("You are operating with the following organizational context.")
        lines.append("Respect every constraint and embody every value in your outputs.")
        lines.append("")

        constraints = self.graph.get_nodes(node_type="restrict")
        if constraints:
            lines.append("HARD CONSTRAINTS — never violate these:")
            for c in constraints:
                lines.append(f"- {c['label']}: {c['detail']}")
            lines.append("")

        values = self.graph.get_nodes(node_type="value")
        if values:
            lines.append("CORE VALUES:")
            for v in values:
                lines.append(f"- {v['label']}: {v['detail']}")
            lines.append("")

        brand = self.graph.get_nodes(node_type="brand")
        if brand:
            lines.append("BRAND IDENTITY:")
            for b in brand:
                lines.append(f"- {b['label']}: {b['detail']}")
            lines.append("")

        tones = self.graph.get_nodes(node_type="tone")
        if tones:
            lines.append("TONE & VOICE:")
            for t in tones:
                lines.append(f"- {t['label']}: {t['detail']}")
            lines.append("")

        audiences = self.graph.get_nodes(node_type="audience")
        if audiences:
            lines.append("TARGET AUDIENCES:")
            for a in audiences:
                lines.append(f"- {a['label']}: {a['detail']}")
            lines.append("")

        examples = self.graph.get_nodes(node_type="example")
        if examples:
            lines.append("EXAMPLES OF GOOD COMMUNICATION:")
            for e in examples[:5]:
                lines.append(f"- {e['label']}: {e['detail']}")
            lines.append("")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # CSV — for spreadsheet analysis
    # -----------------------------------------------------------------------

    def to_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "type", "label", "detail", "stability", "weight", "source", "created_at"])
        for node in self.graph.get_nodes():
            writer.writerow([
                node["id"], node["type"], node["label"],
                node["detail"], node["stability"],
                node["weight"], node["source"],
                node.get("created_at", ""),
            ])
        return output.getvalue()

    # -----------------------------------------------------------------------
    # Summary stats
    # -----------------------------------------------------------------------

    def stats(self) -> dict:
        nodes = self.graph.get_nodes()
        edges = self.graph.get_edges()
        by_type = {}
        by_stability = {}
        for n in nodes:
            by_type[n["type"]] = by_type.get(n["type"], 0) + 1
            by_stability[n["stability"]] = by_stability.get(n["stability"], 0) + 1

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "by_type": by_type,
            "by_stability": by_stability,
            "nm_graph": self.graph.nm_graph(),
        }
