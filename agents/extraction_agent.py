"""
Extraction Agent — Organizational Knowledge Harness
Converts raw organizational sources into typed nodes and edges via Gemini Flash.
"""

import json
import os
import re
import google.generativeai as genai
from core.graph_engine import GraphEngine


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """
You are a knowledge extraction specialist. Your task is to analyze organizational
source material and extract a structured knowledge graph.

Extract nodes of these types:
- brand: Core identity, mission, what the organization is
- audience: Who they serve, target segments
- value: Core values, principles, beliefs
- tone: Voice, communication style, how they speak
- restrict: Hard constraints — what must never happen in communications
- example: Concrete examples of good or bad communications

For each node, determine stability:
- stable: Clearly stated, official, foundational
- watch: Implied or uncertain, needs validation
- flagged: Speculative, contradictory, or ambiguous

Extract edges using these relations:
- targets: audience targets a segment
- reaches: brand reaches an audience
- embodies: brand embodies a value
- shapes: value shapes tone
- constrains: value or restrict constrains output
- constrained_by: element is constrained by another
- exemplified_by: concept exemplified_by an example
- validates: element validates another
- limits: element limits another

CRITICAL RULES:
1. Build a STRUCTURED TREE, not a ball of yarn
2. Every restrict node must have at least one edge
3. Prefer fewer, stronger nodes over many weak ones
4. Be precise — "We never use jargon" is better than "We value clarity"
5. Stability = flagged means you are uncertain or saw contradictions

Respond ONLY with valid JSON in this exact format:
{
  "nodes": [
    {
      "type": "value",
      "label": "Authenticity",
      "detail": "Real ingredients, no artificial posturing in any communication",
      "stability": "stable",
      "source_excerpt": "brief quote from source that supports this node"
    }
  ],
  "edges": [
    {
      "from_label": "Authenticity",
      "to_label": "Direct Tone",
      "relation": "shapes"
    }
  ],
  "extraction_notes": "Brief note on what was clear, what was uncertain"
}

Do not include any text outside the JSON object.
"""


# ---------------------------------------------------------------------------
# Extraction Agent
# ---------------------------------------------------------------------------

class ExtractionAgent:
    """
    Transforms raw organizational text into a knowledge graph.
    Uses Gemini Flash for extraction; writes results to GraphEngine.
    """

    def __init__(self, graph: GraphEngine, api_key: str = None):
        self.graph = graph
        api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
        )

    def extract(self, source_text: str, source_name: str = "unknown") -> dict:
        """
        Extract nodes and edges from source text and add to graph.

        Returns:
            dict with extracted nodes, edges, and any errors
        """
        prompt = f"""
Source: {source_name}

---
{source_text[:8000]}
---

Extract the knowledge graph from this organizational source.
"""
        try:
            response = self.model.generate_content(prompt)
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"^```\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            extracted = json.loads(raw)
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse failed: {e}", "raw": raw}
        except Exception as e:
            return {"error": str(e)}

        return self._write_to_graph(extracted, source_name)

    def _write_to_graph(self, extracted: dict, source_name: str) -> dict:
        """Write extracted nodes and edges into the GraphEngine."""
        label_to_id: dict[str, str] = {}
        added_nodes = []
        added_edges = []
        errors = []

        # --- Nodes ---
        for n in extracted.get("nodes", []):
            try:
                node = self.graph.add_node(
                    node_type=n["type"],
                    label=n["label"],
                    detail=n.get("detail", ""),
                    source=source_name,
                    stability=n.get("stability", "stable"),
                )
                label_to_id[n["label"]] = node["id"]
                added_nodes.append(node)
            except Exception as e:
                errors.append(f"Node '{n.get('label')}': {e}")

        # --- Edges ---
        for e in extracted.get("edges", []):
            from_label = e.get("from_label")
            to_label = e.get("to_label")
            relation = e.get("relation")

            from_id = label_to_id.get(from_label)
            to_id = label_to_id.get(to_label)

            if not from_id:
                errors.append(f"Edge source not found: '{from_label}'")
                continue
            if not to_id:
                errors.append(f"Edge target not found: '{to_label}'")
                continue

            try:
                edge = self.graph.add_edge(from_id, to_id, relation)
                added_edges.append(edge)
            except Exception as ex:
                errors.append(f"Edge '{from_label}→{to_label}': {ex}")

        # Commit to git
        self.graph.save(
            f"extract: {len(added_nodes)} nodes, {len(added_edges)} edges from '{source_name}'"
        )

        return {
            "nodes_added": len(added_nodes),
            "edges_added": len(added_edges),
            "nodes": added_nodes,
            "edges": added_edges,
            "extraction_notes": extracted.get("extraction_notes", ""),
            "errors": errors,
            "nm_graph": self.graph.nm_graph(),
        }
