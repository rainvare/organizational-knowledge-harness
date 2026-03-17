"""
agents/generation_agent.py
Generates brand-aligned content using the knowledge graph as grounded context.
"""
import json
import re
from core.graph_engine import GraphEngine


class GenerationAgent:
    def __init__(self, graph: GraphEngine, api_key: str):
        self.graph = graph
        self.api_key = api_key

    def _build_context(self) -> tuple[str, list]:
        """Build system prompt context from graph nodes. Returns (context_str, trace)."""
        trace = []
        sections = []

        type_labels = {
            "brand": "BRAND IDENTITY",
            "audience": "TARGET AUDIENCES",
            "value": "CORE VALUES",
            "tone": "TONE & VOICE",
            "color": "COLOR PALETTE",
            "typography": "TYPOGRAPHY SYSTEM",
            "visual": "VISUAL LANGUAGE",
            "restrict": "NEVER DO",
            "example": "GOOD EXAMPLES",
        }

        for node_type, section_title in type_labels.items():
            nodes = self.graph.get_nodes(node_type=node_type)
            if not nodes:
                continue
            lines = [f"\n## {section_title}"]
            for n in nodes:
                lines.append(f"- [{n['label']}]: {n['detail']}")
                trace.append({
                    "node_id": n["id"],
                    "node_type": n["type"],
                    "node_label": n["label"],
                    "role": section_title,
                })
            sections.append("\n".join(lines))

        context = "\n".join(sections)
        return context, trace

    def generate(self, task: str, content_type: str = "general") -> dict:
        context, trace = self._build_context()

        system = f"""You are a brand-aligned content writer. You must strictly follow the organizational guidelines below.

ORGANIZATIONAL KNOWLEDGE GRAPH:
{context}

RULES:
1. Every word must reflect the values and tone defined above
2. NEVER violate any restriction listed under "NEVER DO"
3. Write FOR the target audiences defined above
4. Content type: {content_type}
5. Be direct, specific, and on-brand
6. After the content, add a brief line: COHERENCE NOTE: [how this aligns with the brand]"""

        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": task},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            raw = response.choices[0].message.content.strip()

            # Extract coherence note if present
            coherence_notes = ""
            if "COHERENCE NOTE:" in raw:
                parts = raw.split("COHERENCE NOTE:", 1)
                content = parts[0].strip()
                coherence_notes = parts[1].strip()
            else:
                content = raw

            return {
                "content": content,
                "coherence_notes": coherence_notes,
                "trace": trace,
                "content_type": content_type,
            }

        except Exception as e:
            return {"error": str(e)}
