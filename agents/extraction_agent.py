"""Extraction Agent — uses Groq/Llama"""
import json, os, re
from groq import Groq
from core.graph_engine import GraphEngine

SYSTEM_PROMPT = """You are a knowledge extraction specialist. Extract a structured knowledge graph from organizational source material.

Extract nodes of these types: brand, audience, value, tone, restrict, example
For each node determine stability: stable, watch, or flagged
Extract edges using: targets, reaches, embodies, shapes, constrains, constrained_by, exemplified_by, validates, limits

Respond ONLY with valid JSON:
{
  "nodes": [{"type":"value","label":"Authenticity","detail":"No artificial posturing","stability":"stable","source_excerpt":"..."}],
  "edges": [{"from_label":"Authenticity","to_label":"Direct Tone","relation":"shapes"}],
  "extraction_notes": "brief note"
}"""

class ExtractionAgent:
    def __init__(self, graph: GraphEngine, api_key: str = None):
        self.graph = graph
        api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.client = Groq(api_key=api_key)

    def extract(self, source_text: str, source_name: str = "unknown") -> dict:
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Source: {source_name}\n\n{source_text[:6000]}"}
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw)
            extracted = json.loads(raw)
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse failed: {e}"}
        except Exception as e:
            return {"error": str(e)}

        return self._write_to_graph(extracted, source_name)

    def _write_to_graph(self, extracted, source_name):
        label_to_id = {}
        added_nodes, added_edges, errors = [], [], []

        for n in extracted.get("nodes", []):
            try:
                node = self.graph.add_node(
                    node_type=n["type"], label=n["label"],
                    detail=n.get("detail",""), source=source_name,
                    stability=n.get("stability","stable"),
                )
                label_to_id[n["label"]] = node["id"]
                added_nodes.append(node)
            except Exception as e:
                errors.append(f"Node '{n.get('label')}': {e}")

        for e in extracted.get("edges", []):
            from_id = label_to_id.get(e.get("from_label"))
            to_id = label_to_id.get(e.get("to_label"))
            if not from_id or not to_id:
                continue
            try:
                edge = self.graph.add_edge(from_id, to_id, e["relation"])
                added_edges.append(edge)
            except Exception as ex:
                errors.append(str(ex))

        self.graph.save(f"extract: {len(added_nodes)} nodes from '{source_name}'")
        return {
            "nodes_added": len(added_nodes), "edges_added": len(added_edges),
            "nodes": added_nodes, "edges": added_edges,
            "extraction_notes": extracted.get("extraction_notes",""),
            "errors": errors, "nm_graph": self.graph.nm_graph(),
        }
