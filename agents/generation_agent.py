"""Generation Agent — uses Groq/Llama"""
import json, os, re
from groq import Groq
from core.graph_engine import GraphEngine

SYSTEM_PROMPT = """You are a content generation specialist operating inside a structured knowledge graph.
Query the graph context provided. Check constraints FIRST. Never violate restrict nodes.

Respond ONLY with valid JSON:
{
  "content": "generated text here",
  "trace": [{"node_id":"...","node_label":"...","node_type":"...","role":"..."}],
  "coherence_notes": "brief note"
}"""

class GenerationAgent:
    def __init__(self, graph: GraphEngine, api_key: str = None):
        self.graph = graph
        api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.client = Groq(api_key=api_key)

    def generate(self, task: str, content_type: str = "general") -> dict:
        nm = self.graph.nm_graph()
        if nm["state"] == "unstable":
            return {"error": "Graph unstable (NM < 0).", "nm_graph": nm}

        context = self._build_context()
        prompt = f"Task: {task}\nType: {content_type}\n\n--- GRAPH ---\n{context}\n--- END ---\n\nGenerate content."

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw)
            result = json.loads(raw)
        except json.JSONDecodeError:
            return {"content": response.choices[0].message.content, "trace": [], "coherence_notes": "trace unavailable", "nm_graph": nm}
        except Exception as e:
            return {"error": str(e), "nm_graph": nm}

        result["nm_graph"] = nm
        result["task"] = task
        return result

    def _build_context(self) -> str:
        lines = []
        constraints = self.graph.get_constraints()
        if constraints:
            lines.append("## HARD CONSTRAINTS")
            for c in constraints:
                lines.append(f"- [{c['id']}] {c['label']}: {c['detail']}")
            lines.append("")
        for node_type, heading in [("value","## VALUES"),("brand","## BRAND"),("audience","## AUDIENCES"),("tone","## TONE"),("example","## EXAMPLES")]:
            nodes = self.graph.get_nodes(node_type=node_type)
            if nodes:
                lines.append(heading)
                for n in nodes[:5]:
                    lines.append(f"- [{n['id']}] {n['label']}: {n['detail']}")
                lines.append("")
        return "\n".join(lines)
