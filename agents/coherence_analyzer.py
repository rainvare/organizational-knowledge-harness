"""
Coherence Analyzer — Organizational Knowledge Harness Sprint 2+3
source field differentiates internal vs external signals (Sprint 3).
"""

import json, os, re
from datetime import datetime, timezone
from uuid import uuid4
import google.generativeai as genai
from core.graph_engine import GraphEngine

COHERENCE_SYSTEM_PROMPT = """
You are a coherence analyst evaluating generated content against a knowledge graph.

For each node:
- restrict: PASS or FAIL
- value/tone/audience: score 0.0-1.0
- brand/example: skip (null)

Also provide signal_type: aligned | drifting | violation | neutral
And confidence: 0.0-1.0, note: one sentence.

Respond ONLY with valid JSON:
{
  "node_scores": [
    {"node_id":"...","node_label":"...","node_type":"...","score":"pass","signal_type":"aligned","confidence":0.9,"note":"..."}
  ],
  "global_coherence": 0.84,
  "summary": "one sentence"
}
"""

class CoherenceAnalyzer:
    def __init__(self, graph: GraphEngine, api_key: str = None):
        self.graph = graph
        api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=COHERENCE_SYSTEM_PROMPT,
        )

    def analyze(self, content: str, task: str = "", cycle: int = 0, source: str = "internal") -> dict:
        nodes = self.graph.get_nodes()
        if not nodes:
            return {"error": "Graph is empty"}

        node_ctx = "\n".join(
            f"[{n['id']}] type={n['type']} label=\"{n['label']}\" detail=\"{n['detail'][:100]}\" stability={n['stability']}"
            for n in nodes if n["type"] not in ("brand", "example")
        )
        source_label = "External AI output" if source == "external" else "Internally generated"

        prompt = f"Source type: {source_label}\nTask: {task}\n\nContent:\n---\n{content}\n---\n\nNodes:\n{node_ctx}\n\nEvaluate coherence."
        try:
            response = self.model.generate_content(prompt)
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", response.text.strip())
            result = json.loads(raw)
        except Exception as e:
            return {"error": str(e)}

        signals = self._build_signals(result.get("node_scores", []), cycle, source)
        return {
            "node_scores": result.get("node_scores", []),
            "global_coherence": result.get("global_coherence"),
            "summary": result.get("summary", ""),
            "signals": signals,
            "cycle": cycle,
            "source": source,
            "content_preview": content[:200],
        }

    def _build_signals(self, node_scores, cycle, source="internal"):
        now = datetime.now(timezone.utc).isoformat()
        signals = []
        for ns in node_scores:
            st = ns.get("signal_type", "neutral")
            signals.append({
                "id": f"sig_{uuid4().hex[:8]}",
                "node_id": ns.get("node_id"),
                "node_label": ns.get("node_label"),
                "node_type": ns.get("node_type"),
                "signal_type": st,
                "score": ns.get("score"),
                "confidence": ns.get("confidence", 0.5),
                "severity": "high" if st == "violation" else "medium" if st == "drifting" else "low",
                "note": ns.get("note", ""),
                "cycle": cycle,
                "source": source,
                "created_at": now,
            })
        return signals
