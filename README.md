---
title: Organizational Knowledge Harness
emoji: 🕸️
colorFrom: yellow
colorTo: gray
sdk: streamlit
sdk_version: 1.32.0
app_file: app.py
pinned: false
---

# Organizational Knowledge Harness
A living context engine that learns from use.

**Live demo:** [huggingface.co/spaces/Rainvare/organizacional-knowledge-harness](https://huggingface.co/spaces/Rainvare/organizacional-knowledge-harness)

---

## Architecture

Built on Harness Engineering (Böckeler, Thoughtworks 2026):

| Harness layer | Implementation |
|---|---|
| Context engineering | Extraction Agent + Graph Engine |
| Architectural constraints | NM_graph + Coherence Analyzer |
| Garbage collection | Evidence Accumulator + Proposal Queue |

---

## Sprints delivered

| Sprint | What it does |
|---|---|
| 1 | Ingesta → Grafo → Generación con trace de nodos |
| 2 | Coherence Analyzer + Evidence Accumulator + Proposal Queue |
| 3 | Input externo — aprende de outputs de otras IAs, diferencia fuente interna/externa |
| 4 | Exportación en 4 formatos: prompt.txt, markdown, JSON, CSV |
| 5 | Input multimodal: PDF, PPTX, DOCX, imágenes, URL |
| 5+ | Smart URL parser: Behance, Figma, Dribbble con visión IA |
| 08 | Generador de prompts visuales para Midjourney, DALL-E, Sora, Runway, Kling |

---

## Node types

The graph captures the full formal brand identity system:

| Type | What it captures |
|---|---|
| `brand` | Name, mission, positioning, personality |
| `audience` | Target segments, personas, psychographics |
| `value` | Core organizational values and principles |
| `tone` | Voice, communication style, copy rules |
| `restrict` | Prohibitions — what this brand never does |
| `example` | Reference applications, good/bad copy |
| `color` | Palette entries with HEX codes and usage rules |
| `typography` | Typefaces with name, weight, role, and hierarchy |
| `visual` | Logo system, layout, photography style, graphic elements |

---

## Smart URL ingestion

The URL parser routes automatically by source type:

| Source | Strategy |
|---|---|
| **Behance / Dribbble** | Scraping + multi-image Groq vision analysis + LLM synthesis |
| **Figma** (public) | oEmbed metadata + thumbnail vision analysis |
| **Figma** (with token) | Full API — exact HEX colors, font names, component structure |
| **Generic URLs** | BeautifulSoup + Open Graph + JSON-LD structured data |

Paste a Behance project URL and get a typed brand graph in ~30 seconds — including color palette, typography system, logo rules, and visual language.

---

## Stack

| Component | Technology |
|---|---|
| Frontend + Backend | Streamlit |
| LLM | Groq — `llama-3.3-70b-versatile` (free tier) |
| Vision | Groq — `llama-3.2-11b-vision-preview` |
| Graph persistence | JSON + git-native versioning |
| Hosting | Hugging Face Spaces |

---

## Setup

```bash
git clone https://github.com/rainvare/organizational-knowledge-harness
cd organizational-knowledge-harness
pip install -r requirements.txt

# Get a free API key at console.groq.com
export GROQ_API_KEY=gsk_your_key_here

streamlit run app.py
```

Or enter the key directly in the sidebar of the running app.

---

## NM_graph — stability metric

Adapted from the Muñoz Number (UFAL, DOI: 10.5281/zenodo.18653104):

```
F = flagged_nodes / total_nodes
C = control_edges / total_edges
NM_graph = -ln(F / C)

> 0.5  → stable
0–0.5  → watch
≈ 0    → bifurcation (requests validation)
< 0    → unstable (blocks generation)
```

---

## Theoretical basis

- **Harness Engineering** — Böckeler (Thoughtworks, Feb 2026)
- **NM_graph** — adapted from Muñoz Number / UFAL (DOI: 10.5281/zenodo.18653104)
- **AI as reasoning partner** — Knuth / Claude's Cycles (Stanford, Feb 2026)
- **Multimodal input** — MANGO (NeurIPS 2025): per-modality preprocessing prevents signal dominance

---

## Portfolio context

```
context-graph-engine              → concept demo (vis.js + Claude API)
context-curator                   → ingestion + extraction (browser-based)
organizational-knowledge-harness  → full harness platform (this repo)
```

Three projects, one thesis: structured context governs better than unstructured prompts.

---
*Indira Valentina Réquiz · [github.com/rainvare](https://github.com/rainvare)*  
*Lingüística (UCV 2017) · MBA Business Intelligence (UNIR)*
