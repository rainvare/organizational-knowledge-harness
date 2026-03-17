# Organizational Knowledge Harness

A living context engine that learns from use.

## Architecture

Built on Harness Engineering (Böckeler, Thoughtworks 2026):

| Harness layer | Implementation |
|---|---|
| Context engineering | Extraction Agent + Graph Engine |
| Architectural constraints | NM_graph + Coherence Analyzer |
| Garbage collection | Evidence Accumulator + Proposal Queue |

## Sprints delivered

| Sprint | What it does |
|---|---|
| 1 | Ingesta → Grafo → Generación con trace de nodos |
| 2 | Coherence Analyzer + Evidence Accumulator + Proposal Queue |
| 3 | Input externo — aprende de outputs de otras IAs, diferencia fuente |
| 4 | Exportación en 4 formatos: prompt, markdown, JSON, CSV |
| 5 | Input multimodal: PDF, PPTX, DOCX, imágenes, URL |

## Stack

| Component | Technology |
|---|---|
| Frontend + Backend | Streamlit |
| LLM | Gemini Flash (free tier) |
| Graph persistence | JSON + git versioning |
| Hosting | Hugging Face Spaces |

## Setup

```bash
git clone https://github.com/your-username/organizational-knowledge-harness
cd organizational-knowledge-harness
pip install -r requirements.txt

# Optional: multimodal parsers
pip install PyMuPDF python-pptx python-docx

export GEMINI_API_KEY=your_key_here
streamlit run frontend/app.py
```

## Theoretical basis

- **Harness Engineering** — Böckeler (Thoughtworks, Feb 2026)
- **NM_graph** — adapted from Muñoz Number / UFAL (DOI: 10.5281/zenodo.18653104)
- **AI as reasoning partner** — Knuth / Claude's Cycles (Stanford, Feb 2026)
- **Multimodal input** — MANGO (NeurIPS 2025): per-modality preprocessing prevents signal dominance

## Portfolio context

```
context-graph-engine              → concept demo
context-curator                   → ingestion + extraction
organizational-knowledge-harness  → full harness platform
```

---
*R. Indira Valentina Réquiz*
