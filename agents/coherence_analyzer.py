"""Coherence Analyzer — uses Groq/Llama"""
import json, os, re
from datetime import datetime, timezone
from uuid import uuid4
from groq import Groq
from core.graph_engine import GraphEngine

SYSTEM_PROMPT = """Evaluate whether generated content aligns with knowledge graph nodes.
For restrict nodes: pass or fail. For value/tone/audience: score 0.0-1.0.
signal_type: aligned, drifting, violation, or neutral.

Respond ONLY with valid JSON:
{
  "node_scores": [{"node_id":"...","node_label":"...","node_type":"...","score":"pass","signal_type":"aligned","confidence":0.9,"note":"..."}],
  "global_coherence": 0.84,
  "summary": "one sentence"
}"""

class CoherenceAnalyzer:
    def __init__(self, graph: GraphEngine, api_key: str = None):
        self.graph = graph
        api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.client = Groq(api_key=api_key)

    def analyze(self, content: str, task: str = "", cycle: int = 0, source: str = "internal") -> dict:
        nodes = self.graph.get_nodes()
        if not nodes:
            return {"error": "Graph is empty"}

        node_ctx = "\n".join(
            f"[{n['id']}] type={n['type']} label=\"{n['label']}\" detail=\"{n['detail'][:80]}\""
            for n in nodes if n["type"] not in ("brand","example")
        )

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Task: {task}\n\nContent:\n{content}\n\nNodes:\n{node_ctx}"}
                ],
                temperature=0.1,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw)
            result = json.loads(raw)
        except Exception as e:
            return {"error": str(e)}

        signals = self._build_signals(result.get("node_scores",[]), cycle, source)
        return {
            "node_scores": result.get("node_scores",[]),
            "global_coherence": result.get("global_coherence"),
            "summary": result.get("summary",""),
            "signals": signals, "cycle": cycle, "source": source,
            "content_preview": content[:200],
        }

    def _build_signals(self, node_scores, cycle, source="internal"):
        now = datetime.now(timezone.utc).isoformat()
        signals = []
        for ns in node_scores:
            st = ns.get("signal_type","neutral")
            signals.append({
                "id": f"sig_{uuid4().hex[:8]}",
                "node_id": ns.get("node_id"), "node_label": ns.get("node_label"),
                "node_type": ns.get("node_type"), "signal_type": st,
                "score": ns.get("score"), "confidence": ns.get("confidence",0.5),
                "severity": "high" if st=="violation" else "medium" if st=="drifting" else "low",
                "note": ns.get("note",""), "cycle": cycle, "source": source, "created_at": now,
            })
        return signals
