"""
agents/extraction_agent.py
Extracts typed knowledge graph nodes and edges from organizational text.
Uses Groq/Llama-3.3-70b (free tier).
"""
import json
import re
from typing import Optional
from core.graph_engine import GraphEngine


SYSTEM_PROMPT = """You are an organizational knowledge extraction engine specialized in brand identity.

Extract a structured knowledge graph from the text. Output ONLY valid JSON, no preamble, no markdown.

Node types:
- brand: brand name, mission, positioning, personality, archetype
- audience: target segments, personas, demographics, psychographics
- value: core organizational/brand values, beliefs, principles
- tone: communication tone, voice attributes, copy style, language rules
- restrict: things to NEVER do — design, copy, or behavior prohibitions
- example: concrete examples of good/bad communication or design application
- color: a specific color or color role in the palette (include HEX if available)
- typography: a specific typeface or typographic role (include font name, weight, role)
- visual: visual language rules — logo system, layout, graphic elements, photography style, spacing

For each node extract:
- type: one of [brand, audience, value, tone, restrict, example, color, typography, visual]
- label: short name (3-6 words max), e.g. "Primary Brown #3B1F0E", "Headline Typeface Playfair", "Logo Clear Space Rule"
- detail: precise description (1-3 sentences). For color nodes include HEX/RGB if available. For typography nodes include font name, weight, classification. For visual nodes describe the rule concretely.
- stability: "stable" (core identity) | "watch" (may evolve) | "flagged" (uncertain/contradictory)

For edges extract meaningful relationships:
- from_label, to_label, relation
  Valid relations: targets, embodies, shapes, constrains, constrained_by, exemplified_by,
  validates, limits, applies_to, contrasts_with, pairs_with, defines, governs
- is_control: true if this edge represents a structural design constraint

IMPORTANT: Extract color, typography, and visual nodes whenever that information is present.
If you see color descriptions like "warm chocolate brown", create a color node.
If you see font mentions like "Playfair Display for headlines", create a typography node.
If you see layout or logo rules, create visual nodes.

Respond ONLY with this JSON:
{
  "nodes": [
    {"type": "color", "label": "Primary Brown #3B1F0E", "detail": "Deep chocolate brown, primary brand color. Used for headlines, key UI, and logo. Communicates warmth and craftsmanship.", "stability": "stable"},
    {"type": "typography", "label": "Headline Serif Playfair Display", "detail": "Playfair Display, high-contrast serif. Used for all headlines at Regular and Bold weights. Communicates elegance and editorial refinement.", "stability": "stable"}
  ],
  "edges": [
    {"from_label": "Primary Brown #3B1F0E", "to_label": "Headline Serif Playfair Display", "relation": "pairs_with", "is_control": false}
  ],
  "extraction_notes": "brief summary of what was found and quality of brand data"
}"""


class ExtractionAgent:
    def __init__(self, graph: GraphEngine, api_key: str):
        self.graph = graph
        self.api_key = api_key

    def extract(self, text: str, source_name: str = "source") -> dict:
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            # Truncate to avoid token limits
            text_chunk = text[:8000]

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Source: {source_name}\n\n{text_chunk}"},
                ],
                temperature=0.2,
                max_tokens=4000,
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE)

            data = json.loads(raw)

        except json.JSONDecodeError as e:
            return {"error": f"LLM returned invalid JSON: {e}", "raw": raw}
        except Exception as e:
            return {"error": str(e)}

        nodes_added = 0
        edges_added = 0
        errors = []
        label_to_id: dict = {}

        for node in data.get("nodes", []):
            try:
                nid = self.graph.add_node(
                    node_type=node["type"],
                    label=node["label"],
                    detail=node["detail"],
                    source=source_name,
                    stability=node.get("stability", "stable"),
                )
                label_to_id[node["label"].lower()] = nid
                nodes_added += 1
            except Exception as e:
                errors.append(f"Node '{node.get('label', '?')}': {e}")

        # Build reverse lookup from existing nodes too
        for nid, n in self.graph._nodes.items():
            label_to_id[n["label"].lower()] = nid

        for edge in data.get("edges", []):
            try:
                fl = edge.get("from_label", "").lower()
                tl = edge.get("to_label", "").lower()
                from_id = label_to_id.get(fl)
                to_id = label_to_id.get(tl)
                if from_id and to_id:
                    self.graph.add_edge(
                        from_id=from_id,
                        to_id=to_id,
                        relation=edge.get("relation", "relates_to"),
                        is_control=edge.get("is_control", False),
                    )
                    edges_added += 1
                else:
                    errors.append(f"Edge '{edge.get('from_label')}' → '{edge.get('to_label')}': node(s) not found")
            except Exception as e:
                errors.append(f"Edge error: {e}")

        self.graph.save(f"extract: {nodes_added} nodes from '{source_name}'")

        return {
            "nodes_added": nodes_added,
            "edges_added": edges_added,
            "errors": errors,
            "extraction_notes": data.get("extraction_notes", ""),
        }
