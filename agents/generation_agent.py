"""
Generation Agent — Organizational Knowledge Harness
Generates content by traversing the knowledge graph during reasoning.
Every output includes a trace of which nodes authorized each decision.
"""

import json
import os
import re
import google.genai as genai
from core.graph_engine import GraphEngine


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

GENERATION_SYSTEM_PROMPT = """
You are a content generation specialist operating inside a structured knowledge graph.
You have access to tools that let you query the graph during generation.

Your process:
1. Query the graph BEFORE writing anything
2. Check constraints FIRST — these are hard limits
3. Identify relevant values and tone nodes
4. Find examples if available
5. Generate content that respects every node you consulted
6. Report exactly which nodes authorized your decisions

You must NEVER:
- Generate content that violates any restrict node
- Ignore constraints even if they limit creativity
- Produce output without consulting the graph first

Format your response as JSON:
{
  "content": "The generated content here",
  "trace": [
    {
      "node_id": "res_abc123",
      "node_label": "No Hustle Culture",
      "node_type": "restrict",
      "role": "This node prohibited language around overwork or grind mentality"
    }
  ],
  "coherence_notes": "Brief note on how well this output aligns with the graph"
}
"""


# ---------------------------------------------------------------------------
# Generation Agent
# ---------------------------------------------------------------------------

class GenerationAgent:
    """
    Generates content using the knowledge graph as an operational environment.
    Traverses nodes during generation and produces a full trace.
    """

    def __init__(self, graph: GraphEngine, api_key: str = None):
        self.graph = graph
        api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=GENERATION_SYSTEM_PROMPT,
        )

    def generate(self, task: str, content_type: str = "general") -> dict:
        """
        Generate content for a given task, traversing the graph.

        Args:
            task: What to generate (e.g. "Write a LinkedIn post about our new product")
            content_type: Type hint for generation (post, email, bio, tagline, etc.)

        Returns:
            dict with content, trace, coherence_notes, and nm_graph state
        """
        # --- Check graph stability before generating ---
        nm = self.graph.nm_graph()
        if nm["state"] == "unstable":
            return {
                "error": "Graph is unstable (NM_graph < 0). Resolve flagged nodes before generating.",
                "nm_graph": nm,
            }

        # --- Build graph context for the prompt ---
        context = self._build_context()

        prompt = f"""
Task: {task}
Content type: {content_type}

--- KNOWLEDGE GRAPH ---
{context}
--- END GRAPH ---

Generate content for this task using the graph above.
Consult every relevant node. Check constraints first.
Report your trace in the response JSON.
"""
        try:
            response = self.model.generate_content(prompt)
            raw = response.text.strip()

            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"^```\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            result = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: return raw text without trace
            return {
                "content": response.text,
                "trace": [],
                "coherence_notes": "Trace unavailable — JSON parse failed",
                "nm_graph": nm,
            }
        except Exception as e:
            return {"error": str(e), "nm_graph": nm}

        result["nm_graph"] = nm
        result["task"] = task
        return result

    def _build_context(self) -> str:
        """Serialize graph into a structured prompt context."""
        lines = []

        # Constraints first — always
        constraints = self.graph.get_constraints()
        if constraints:
            lines.append("## HARD CONSTRAINTS (must never violate)")
            for c in constraints:
                flag = " [FLAGGED - low confidence]" if c["stability"] == "flagged" else ""
                lines.append(f"- [{c['id']}] {c['label']}: {c['detail']}{flag}")
            lines.append("")

        # Values
        values = self.graph.get_nodes(node_type="value")
        if values:
            lines.append("## CORE VALUES")
            for v in values:
                lines.append(f"- [{v['id']}] {v['label']}: {v['detail']}")
            lines.append("")

        # Brand
        brand = self.graph.get_nodes(node_type="brand")
        if brand:
            lines.append("## BRAND IDENTITY")
            for b in brand:
                lines.append(f"- [{b['id']}] {b['label']}: {b['detail']}")
            lines.append("")

        # Audiences
        audiences = self.graph.get_nodes(node_type="audience")
        if audiences:
            lines.append("## TARGET AUDIENCES")
            for a in audiences:
                lines.append(f"- [{a['id']}] {a['label']}: {a['detail']}")
            lines.append("")

        # Tone
        tones = self.graph.get_nodes(node_type="tone")
        if tones:
            lines.append("## TONE & VOICE")
            for t in tones:
                lines.append(f"- [{t['id']}] {t['label']}: {t['detail']}")
            lines.append("")

        # Examples
        examples = self.graph.get_nodes(node_type="example")
        if examples:
            lines.append("## EXAMPLES")
            for e in examples[:5]:  # cap at 5 to keep context manageable
                lines.append(f"- [{e['id']}] {e['label']}: {e['detail']}")
            lines.append("")

        # Edges — structural relationships
        edges = self.graph.get_edges()
        if edges:
            lines.append("## STRUCTURAL RELATIONSHIPS")
            for e in edges:
                from_node = self.graph.get_node(e["from"])
                to_node = self.graph.get_node(e["to"])
                if from_node and to_node:
                    lines.append(
                        f"- {from_node['label']} --[{e['relation']}]--> {to_node['label']}"
                    )

        return "\n".join(lines)
