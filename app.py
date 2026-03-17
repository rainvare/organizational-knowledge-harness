"""
Organizational Knowledge Harness — Full App (Sprints 1-5)
Tabs: Ingesta · Grafo · Generación · Coherencia · Propuestas · Exportar · Historial
"""
import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from core.graph_engine import GraphEngine
from agents.extraction_agent import ExtractionAgent
from agents.generation_agent import GenerationAgent
from agents.coherence_analyzer import CoherenceAnalyzer
from agents.evidence_accumulator import EvidenceAccumulator
from agents.proposal_queue import ProposalQueue
from agents.context_exporter import ContextExporter

st.set_page_config(page_title="Organizational Knowledge Harness", page_icon="🕸️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300&display=swap');
:root{--bg:#0e0f0f;--s:#161718;--s2:#1e2021;--b:#2a2c2d;--tx:#e8e4df;--tm:#7a7672;--ac:#c8a96e;--as:rgba(200,169,110,0.12);--gn:#5a9e72;--yw:#c8a96e;--rd:#b05c5c;--bl:#5c8fb0;--pu:#9678b4;}
html,body,[class*="css"]{font-family:'DM Mono',monospace;background-color:var(--bg)!important;color:var(--tx)!important;}
h1,h2,h3{font-family:'Fraunces',serif!important;font-weight:300!important;color:var(--tx)!important;}
.stButton>button{background:var(--as)!important;border:1px solid var(--ac)!important;color:var(--ac)!important;font-family:'DM Mono',monospace!important;font-size:.8rem!important;border-radius:2px!important;transition:all .15s ease!important;}
.stButton>button:hover{background:var(--ac)!important;color:var(--bg)!important;}
.stTextArea textarea,.stTextInput input,.stSelectbox select{background:var(--s)!important;border:1px solid var(--b)!important;color:var(--tx)!important;font-family:'DM Mono',monospace!important;border-radius:2px!important;}
.stTab [data-baseweb="tab"]{font-family:'DM Mono',monospace!important;color:var(--tm)!important;}
.stTab [aria-selected="true"]{color:var(--ac)!important;border-bottom-color:var(--ac)!important;}
.mc{background:var(--s);border:1px solid var(--b);border-radius:2px;padding:1rem 1.2rem;margin-bottom:.5rem;}
.nm-stable{border-left:3px solid var(--gn);}.nm-watch{border-left:3px solid var(--yw);}
.nm-bifurcation{border-left:3px solid var(--yw);animation:pulse 2s infinite;}.nm-unstable{border-left:3px solid var(--rd);}
.nm-insufficient{border-left:3px solid var(--tm);}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.6;}}
.nc{background:var(--s);border:1px solid var(--b);border-radius:2px;padding:.8rem 1rem;margin-bottom:.4rem;font-size:.82rem;}
.ns{border-left:3px solid var(--gn);}.nw{border-left:3px solid var(--yw);}.nf{border-left:3px solid var(--rd);}
.ti{background:var(--s2);border:1px solid var(--b);border-left:3px solid var(--bl);border-radius:2px;padding:.6rem 1rem;margin-bottom:.3rem;font-size:.78rem;}
.pc{background:var(--s);border:1px solid var(--b);border-left:3px solid var(--pu);border-radius:2px;padding:1rem 1.2rem;margin-bottom:.8rem;}
.tag{display:inline-block;padding:.1rem .5rem;border-radius:2px;font-size:.7rem;margin-right:.3rem;}
.tag-brand{background:rgba(90,158,114,.15);color:#5a9e72;border:1px solid #5a9e72;}
.tag-audience{background:rgba(92,143,176,.15);color:#5c8fb0;border:1px solid #5c8fb0;}
.tag-value{background:rgba(200,169,110,.15);color:#c8a96e;border:1px solid #c8a96e;}
.tag-tone{background:rgba(150,120,180,.15);color:#9678b4;border:1px solid #9678b4;}
.tag-restrict{background:rgba(176,92,92,.15);color:#b05c5c;border:1px solid #b05c5c;}
.tag-example{background:rgba(120,140,120,.15);color:#789078;border:1px solid #789078;}
.src-ext{background:rgba(92,143,176,.1);border:1px solid #5c8fb0;color:#5c8fb0;padding:.1rem .4rem;border-radius:2px;font-size:.68rem;}
.src-int{background:rgba(90,158,114,.1);border:1px solid #5a9e72;color:#5a9e72;padding:.1rem .4rem;border-radius:2px;font-size:.68rem;}
.stSidebar{background:var(--s)!important;border-right:1px solid var(--b)!important;}
div[data-testid="stExpander"]{background:var(--s)!important;border:1px solid var(--b)!important;}
.onboard{background:var(--s2);border:1px solid var(--b);border-left:3px solid var(--ac);border-radius:2px;padding:1.2rem 1.5rem;margin-bottom:1.5rem;}
</style>
""", unsafe_allow_html=True)

# --- State ---
if "graph" not in st.session_state:
    st.session_state.graph = GraphEngine("data/graph_state.json")
if "cycle" not in st.session_state:
    st.session_state.cycle = 0
if "last_gen" not in st.session_state:
    st.session_state.last_gen = None
if "last_coh" not in st.session_state:
    st.session_state.last_coh = None

graph: GraphEngine = st.session_state.graph

def akey(): return st.session_state.get("api_key", os.environ.get("GROQ_API_KEY",""))
def nm_cls(s): return {"stable":"nm-stable","watch":"nm-watch","bifurcation":"nm-bifurcation","unstable":"nm-unstable","insufficient_data":"nm-insufficient"}.get(s,"nm-insufficient")
def ttag(t): return f'<span class="tag tag-{t}">{t}</span>'
def sicon(s): return {"stable":"●","watch":"◐","flagged":"○"}.get(s,"?")
def scol(v):
    if isinstance(v,str): return "var(--gn)" if v=="pass" else "var(--rd)"
    if v is None: return "var(--tm)"
    return "var(--gn)" if v>=.75 else "var(--yw)" if v>=.5 else "var(--rd)"

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🕸️ Knowledge Harness")
    st.markdown("---")
    k = st.text_input("Groq API Key", value=akey(), type="password", placeholder="gsk_...")
    if k: st.session_state.api_key = k
    st.markdown("---")
    nm = graph.nm_graph()
    nv = f"{nm['nm']:.3f}" if isinstance(nm.get("nm"),float) else "—"
    st.markdown(f'<div class="mc {nm_cls(nm["state"])}"><div style="font-size:.7rem;color:var(--tm);margin-bottom:.3rem;">NM_graph STABILITY</div><div style="font-size:1.6rem;color:var(--ac);font-family:\'Fraunces\',serif;">{nv}</div><div style="font-size:.75rem;color:var(--tm);">{nm["state"].upper()}</div></div>', unsafe_allow_html=True)
    if nm.get("f") is not None:
        st.markdown(f'<div style="font-size:.72rem;color:var(--tm);line-height:1.8;">F={nm["f"]} · C={nm["c"]}<br>flagged={nm["flagged_nodes"]}/{nm["total_nodes"]}<br>ctrl edges={nm["control_edges"]}/{nm["total_edges"]}</div>', unsafe_allow_html=True)
    st.markdown("---")
    sm = graph.summary()
    pq = ProposalQueue(graph)
    pc = pq.stats()["pending"]
    st.markdown(f'<div style="font-size:.75rem;color:var(--tm);line-height:2.2;"><b style="color:var(--tx);">nodos</b> {sm["total_nodes"]}<br><b style="color:var(--tx);">edges</b> {sm["total_edges"]}<br><b style="color:var(--tx);">ciclo</b> {st.session_state.cycle}<br><b style="color:{"var(--pu)" if pc else "var(--tm)"};">propuestas</b> {pc}</div>', unsafe_allow_html=True)
    if sm["nodes_by_type"]:
        st.markdown("")
        for t,c in sorted(sm["nodes_by_type"].items()):
            st.markdown(f'{ttag(t)} <span style="font-size:.75rem;">{c}</span>', unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🗑 Resetear grafo", use_container_width=True):
        st.session_state.confirm_reset = True
    if st.session_state.get("confirm_reset"):
        st.warning("¿Segura? Esto borra todos los nodos.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Sí, borrar", key="confirm_yes"):
                graph._nodes = {}
                graph._edges = []
                graph._evidence = []
                graph._proposals = []
                graph.save("reset: graph cleared")
                st.session_state.graph = graph
                st.session_state.last_gen = None
                st.session_state.last_coh = None
                st.session_state.cycle = 0
                st.session_state.confirm_reset = False
                st.rerun()
        with col_no:
            if st.button("Cancelar", key="confirm_no"):
                st.session_state.confirm_reset = False
                st.rerun()

# --- Header ---
st.markdown("# Organizational Knowledge Harness")
st.markdown('<p style="color:var(--tm);font-size:.85rem;">A living context engine that learns from use.</p>', unsafe_allow_html=True)

tabs = st.tabs(["01 · Ingesta","02 · Grafo","03 · Generación","04 · Coherencia","05 · Propuestas","06 · Exportar","07 · Historial"])
t1,t2,t3,t4,t5,t6,t7 = tabs

# ============================================================
# TAB 01 — Ingesta (Sprint 1 + Sprint 5 multimodal)
# ============================================================
with t1:
    st.markdown("### Ingresar fuentes")

    # Onboarding for empty graph
    if not graph.get_nodes():
        st.markdown("""
        <div class="onboard">
        <b style="color:var(--ac);">¿Primera vez?</b><br><br>
        1. Ingresa tu Groq API Key en el sidebar (console.groq.com)<br>
        2. Pega el contenido de tu fuente organizacional (guía de marca, valores, manual de tono)<br>
        3. Haz clic en <b>Extraer grafo</b> — el sistema construye la estructura automáticamente<br>
        4. Ve al tab <b>Grafo</b> para revisar los nodos extraídos<br>
        5. Ve al tab <b>Generación</b> para crear contenido usando el grafo como contexto
        </div>
        """, unsafe_allow_html=True)

    input_method = st.radio("Método de ingesta", ["Texto / Pegar", "Archivo", "URL"], horizontal=True)

    source_name = st.text_input("Nombre de la fuente", placeholder="brand_guidelines_2024.txt")

    source_text = ""
    modality = "text"

    if input_method == "Texto / Pegar":
        source_text = st.text_area("Contenido", height=280,
            placeholder="Pega aquí el contenido organizacional...\n\nEjemplos: guía de marca, valores, manual de tono, descripción de audiencias, ejemplos de comunicación buena/mala.")
        modality = "text"

    elif input_method == "Archivo":
        uploaded = st.file_uploader(
            "Sube un archivo",
            type=["txt","md","pdf","pptx","docx","jpg","jpeg","png","webp"],
            help="Formatos soportados: texto, PDF, PowerPoint, Word, imágenes"
        )
        if uploaded:
            import tempfile, pathlib
            suffix = pathlib.Path(uploaded.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name

            from parsers.router import detect_modality, route
            modality = detect_modality(pathlib.Path(uploaded.name))
            source_name = source_name or uploaded.name

            if modality == "text":
                source_text = open(tmp_path, encoding="utf-8", errors="replace").read()
            elif modality == "pdf":
                from parsers.pdf_parser import PDFParser
                result = PDFParser().parse(tmp_path)
                source_text = result.get("text","")
                if result.get("error"): st.warning(result["error"])
            elif modality == "pptx":
                from parsers.pptx_parser import PPTXParser
                result = PPTXParser(api_key=akey()).parse(tmp_path)
                source_text = result.get("text","")
                if result.get("error"): st.warning(result["error"])
            elif modality == "docx":
                from parsers.docx_parser import DOCXParser
                result = DOCXParser().parse(tmp_path)
                source_text = result.get("text","")
                if result.get("error"): st.warning(result["error"])
            elif modality == "image":
                st.info(f"Imagen detectada ({uploaded.name}). Se describirá via IA al extraer.")
                from parsers.image_parser import ImageParser
                with st.spinner("Describiendo imagen..."):
                    result = ImageParser(api_key=akey()).parse(tmp_path)
                source_text = result.get("text","")
                if result.get("error"): st.warning(result["error"])

            if source_text:
                st.markdown(f'<div class="mc" style="font-size:.78rem;max-height:200px;overflow-y:auto;"><b style="color:var(--tm);">TEXTO EXTRAÍDO ({modality.upper()}) — {len(source_text)} chars</b><br><pre style="white-space:pre-wrap;font-size:.75rem;">{source_text[:800]}{"..." if len(source_text)>800 else ""}</pre></div>', unsafe_allow_html=True)

    elif input_method == "URL":
        url_input = st.text_input("URL", placeholder="https://...")
        if url_input:
            modality = "url"
            source_name = source_name or url_input
            from parsers.url_parser import URLParser
            with st.spinner("Fetching URL..."):
                result = URLParser().parse(url_input)
            source_text = result.get("text","")
            if result.get("error"): st.warning(result["error"])
            if source_text:
                st.success(f"✓ {len(source_text)} chars extraídos de {url_input}")

    col_types, col_btn = st.columns([2,1])
    with col_types:
        st.markdown('<div style="font-size:.75rem;color:var(--tm);margin-top:.5rem;">brand · audience · value · tone · restrict · example</div>', unsafe_allow_html=True)
    with col_btn:
        extract_btn = st.button("Extraer grafo →", use_container_width=True)

    if extract_btn:
        if not source_text.strip():
            st.error("No hay contenido para extraer.")
        elif not akey():
            st.error("Ingresa tu Groq API Key en el sidebar.")
        else:
            with st.spinner("Extrayendo grafo..."):
                agent = ExtractionAgent(graph, api_key=akey())
                result = agent.extract(source_text, source_name or "fuente")
                st.session_state.graph = graph
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(f"✓ {result['nodes_added']} nodos · {result['edges_added']} edges extraídos de {modality.upper()}")
                if result.get("extraction_notes"):
                    st.markdown(f'<div class="mc"><span style="font-size:.7rem;color:var(--tm);">NOTAS DE EXTRACCIÓN</span><br><span style="font-size:.82rem;">{result["extraction_notes"]}</span></div>', unsafe_allow_html=True)
                if result.get("errors"):
                    with st.expander(f"⚠ {len(result['errors'])} advertencias"):
                        for e in result["errors"]: st.markdown(f"- {e}")

# ============================================================
# TAB 02 — Grafo
# ============================================================
with t2:
    st.markdown("### Estado del grafo")
    if not graph.get_nodes():
        st.markdown('<p style="color:var(--tm);">Grafo vacío. Ingresa fuentes en la pestaña Ingesta.</p>', unsafe_allow_html=True)
    else:
        c1,c2,c3 = st.columns(3)
        with c1: ft = st.selectbox("Tipo",["todos"]+sorted(["brand","audience","value","tone","restrict","example"]))
        with c2: fs = st.selectbox("Estabilidad",["todos","stable","watch","flagged"])
        with c3:
            if st.button("+ Nodo manual"):
                st.session_state.show_add_node = True

        nodes = graph.get_nodes(
            node_type=None if ft=="todos" else ft,
            stability=None if fs=="todos" else fs,
        )
        st.markdown(f'<p style="font-size:.74rem;color:var(--tm);">{len(nodes)} nodos</p>', unsafe_allow_html=True)

        # Manual node add form
        if st.session_state.get("show_add_node"):
            with st.form("add_node_form"):
                st.markdown("**Agregar nodo manualmente**")
                nc1,nc2 = st.columns(2)
                with nc1:
                    nn_type = st.selectbox("Tipo",["brand","audience","value","tone","restrict","example"])
                    nn_label = st.text_input("Label")
                with nc2:
                    nn_stability = st.selectbox("Estabilidad",["stable","watch","flagged"])
                    nn_source = st.text_input("Fuente","manual")
                nn_detail = st.text_area("Detalle",height=80)
                if st.form_submit_button("Agregar"):
                    if nn_label and nn_detail:
                        graph.add_node(nn_type,nn_label,nn_detail,source=nn_source,stability=nn_stability)
                        graph.save(f"add: manual node '{nn_label}'")
                        st.session_state.show_add_node = False
                        st.rerun()

        for node in sorted(nodes, key=lambda n:(n["type"],n["label"])):
            edges_out = graph.get_edges(from_id=node["id"])
            ehtml = ""
            if edges_out:
                parts = []
                for e in edges_out:
                    tgt = graph.get_node(e["to"])
                    if tgt: parts.append(f'<span style="color:var(--ac);">{e["relation"]}</span> → {tgt["label"]}')
                if parts: ehtml = f'<div style="font-size:.72rem;color:var(--tm);border-top:1px solid var(--b);padding-top:.3rem;margin-top:.3rem;">{" · ".join(parts)}</div>'

            stability_css = {"stable":"ns","watch":"nw","flagged":"nf"}.get(node["stability"],"ns")
            st.markdown(f"""
            <div class="nc {stability_css}">
                <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;">
                    {ttag(node["type"])}<b style="font-size:.85rem;">{node["label"]}</b>
                    <span style="color:var(--tm);font-size:.74rem;margin-left:auto;">{sicon(node["stability"])} {node["stability"]}</span>
                </div>
                <div style="color:var(--tm);font-size:.78rem;margin-bottom:.3rem;">{node["detail"]}</div>
                {ehtml}
            </div>""", unsafe_allow_html=True)

# ============================================================
# TAB 03 — Generación
# ============================================================
with t3:
    st.markdown("### Generar contenido")

    nm_cur = graph.nm_graph()
    if nm_cur["state"] == "unstable":
        st.error("⚠ Grafo inestable (NM_graph < 0). Resuelve nodos flagged antes de generar.")
    elif nm_cur["state"] == "bifurcation":
        st.warning("⚠ Grafo en bifurcación (NM_graph ≈ 0). Considera validar nodos inciertos.")

    c1,c2 = st.columns([3,1])
    with c1:
        task = st.text_area("Tarea",height=100,placeholder="Ej: Escribe un post de LinkedIn anunciando el lanzamiento de nuestro nuevo producto. Tono directo, sin hipérbole.")
    with c2:
        ct = st.selectbox("Tipo",["post","email","bio","tagline","descripción","general"])
        auto_coh = st.checkbox("Analizar coherencia",value=True)

    if st.button("Generar →",use_container_width=True):
        if not task.strip(): st.error("Describe la tarea.")
        elif not akey(): st.error("Ingresa tu Groq API Key.")
        elif not graph.get_nodes(): st.error("Grafo vacío.")
        else:
            with st.spinner("Generando..."):
                gen = GenerationAgent(graph, api_key=akey())
                result = gen.generate(task, ct)
                st.session_state.last_gen = result
                st.session_state.cycle += 1

            if "error" in result:
                st.error(result["error"])
            elif auto_coh and result.get("content"):
                with st.spinner("Analizando coherencia..."):
                    ana = CoherenceAnalyzer(graph, api_key=akey())
                    coh = ana.analyze(result["content"], task, cycle=st.session_state.cycle, source="internal")
                    st.session_state.last_coh = coh
                    if coh.get("signals"):
                        acc = EvidenceAccumulator(graph)
                        new_props = acc.add_signals(coh["signals"])
                        if new_props:
                            st.info(f"💡 {len(new_props)} propuesta(s) nueva(s) — ver tab 05")

    if st.session_state.last_gen and "content" in st.session_state.last_gen:
        r = st.session_state.last_gen
        st.markdown("---")
        st.markdown(f'<div class="mc" style="font-size:.88rem;line-height:1.7;">{r["content"].replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
        trace = r.get("trace",[])
        if trace:
            st.markdown(f"**Trace** — {len(trace)} nodos consultados")
            for item in trace:
                st.markdown(f'<div class="ti">{ttag(item.get("node_type",""))}<b>{item.get("node_label","")}</b><span style="color:var(--tm);font-size:.74rem;"> [{item.get("node_id","")}]</span><br><span style="color:var(--tm);">{item.get("role","")}</span></div>', unsafe_allow_html=True)
        if r.get("coherence_notes"):
            st.markdown(f'<div class="mc"><span style="font-size:.7rem;color:var(--tm);">COHERENCIA</span><br>{r["coherence_notes"]}</div>', unsafe_allow_html=True)

# ============================================================
# TAB 04 — Coherencia (Sprint 2 + Sprint 3)
# ============================================================
with t4:
    st.markdown("### Análisis de coherencia")
    st.markdown('<p style="color:var(--tm);font-size:.82rem;">Mide alineación contra el grafo. Funciona con outputs internos o de cualquier IA externa.</p>', unsafe_allow_html=True)

    # Sprint 3 — external input
    with st.expander("📋 Analizar texto externo (Sprint 3)", expanded=not st.session_state.last_coh):
        ext_text = st.text_area("Texto a analizar", height=150, placeholder="Pega aquí un output generado por cualquier IA usando el contexto de esta organización...")
        ext_task = st.text_input("Tarea original", placeholder="¿Qué se le pidió generar?")
        if st.button("Analizar →", key="analyze_ext"):
            if not ext_text.strip(): st.error("Ingresa texto.")
            elif not akey(): st.error("API Key requerida.")
            elif not graph.get_nodes(): st.error("Grafo vacío.")
            else:
                with st.spinner("Analizando..."):
                    ana = CoherenceAnalyzer(graph, api_key=akey())
                    coh = ana.analyze(ext_text, ext_task, cycle=st.session_state.cycle, source="external")
                    st.session_state.last_coh = coh
                    if coh.get("signals"):
                        acc = EvidenceAccumulator(graph)
                        new_props = acc.add_signals(coh["signals"])
                        if new_props:
                            st.info(f"💡 {len(new_props)} propuesta(s) generada(s)")

    coh = st.session_state.last_coh
    if coh and "node_scores" in coh:
        src = coh.get("source","internal")
        src_badge = f'<span class="src-{"ext" if src=="external" else "int"}">{"EXTERNAL" if src=="external" else "INTERNAL"}</span>'
        gc = coh.get("global_coherence")
        gc_d = f"{gc:.2f}" if gc is not None else "—"
        gc_c = scol(gc) if gc is not None else "var(--tm)"

        st.markdown(f'<div class="mc" style="border-left:3px solid {gc_c};"><div style="font-size:.7rem;color:var(--tm);margin-bottom:.3rem;">COHERENCIA GLOBAL {src_badge}</div><div style="font-size:1.8rem;font-family:\'Fraunces\',serif;color:{gc_c};">{gc_d}</div><div style="font-size:.8rem;color:var(--tm);margin-top:.3rem;">{coh.get("summary","")}</div></div>', unsafe_allow_html=True)

        st.markdown("**Por nodo**")
        for ns in coh.get("node_scores",[]):
            sc = ns.get("score")
            sc_d = sc if isinstance(sc,str) else (f"{sc:.2f}" if sc is not None else "—")
            col = scol(sc)
            sig_col = {"aligned":"var(--gn)","drifting":"var(--yw)","violation":"var(--rd)"}.get(ns.get("signal_type","neutral"),"var(--tm)")
            st.markdown(f'<div class="nc" style="border-left:3px solid {col};"><div style="display:flex;align-items:center;gap:.5rem;">{ttag(ns.get("node_type",""))}<b style="font-size:.82rem;">{ns.get("node_label","")}</b><span style="color:{col};font-size:.85rem;margin-left:auto;font-family:\'Fraunces\',serif;">{sc_d}</span></div><div style="font-size:.75rem;margin-top:.3rem;"><span style="color:{sig_col};">{ns.get("signal_type","").upper()}</span><span style="color:var(--tm);margin-left:.5rem;">conf:{ns.get("confidence",0):.2f}</span><br><span style="color:var(--tm);">{ns.get("note","")}</span></div></div>', unsafe_allow_html=True)

        # Evidence summary with source differentiation
        acc = EvidenceAccumulator(graph)
        sig_sum = acc.signal_summary()
        if sig_sum:
            st.markdown("---")
            st.markdown("**Evidencia acumulada**")
            for nid, data in sig_sum.items():
                # Count by source
                internal_sigs = sum(1 for s in graph._evidence if s["node_id"]==nid and s.get("source","internal")=="internal")
                external_sigs = sum(1 for s in graph._evidence if s["node_id"]==nid and s.get("source")=="external")
                src_info = ""
                if internal_sigs: src_info += f'<span class="src-int">int:{internal_sigs}</span> '
                if external_sigs: src_info += f'<span class="src-ext">ext:{external_sigs}</span>'
                by_t = " · ".join(f"{k}:{v}" for k,v in data["by_type"].items())
                st.markdown(f'<div style="font-size:.78rem;padding:.4rem 0;border-bottom:1px solid var(--b);">{ttag(data["node_type"])}<b>{data["node_label"]}</b> {src_info}<span style="color:var(--tm);margin-left:.5rem;">{by_t}</span></div>', unsafe_allow_html=True)

# ============================================================
# TAB 05 — Propuestas
# ============================================================
with t5:
    st.markdown("### Propuestas de refinamiento")
    st.markdown('<p style="color:var(--tm);font-size:.82rem;">Propuestas generadas cuando ≥3 señales del mismo tipo con confianza promedio ≥0.75.</p>', unsafe_allow_html=True)

    pq = ProposalQueue(graph)
    pending = pq.pending()

    if not pending:
        st.markdown('<div class="mc"><span style="color:var(--tm);">Sin propuestas pendientes. El sistema generará propuestas después de acumular evidencia suficiente.</span></div>', unsafe_allow_html=True)

    for prop in pending:
        ch = prop.get("suggested_change")
        ch_html = ""
        if ch:
            ch_html = f'<div style="background:var(--s2);border:1px solid var(--b);padding:.5rem .8rem;margin:.5rem 0;font-size:.75rem;border-radius:2px;"><span style="color:var(--tm);">campo:</span> {ch["field"]}<br><span style="color:var(--tm);">actual:</span> {ch.get("current","")}<br><span style="color:var(--ac);">sugerido:</span> {ch.get("suggested","")}</div>'

        # Source breakdown in evidence
        int_sigs = sum(1 for s in graph._evidence if s["node_id"]==prop["node_id"] and s.get("source","internal")=="internal")
        ext_sigs = sum(1 for s in graph._evidence if s["node_id"]==prop["node_id"] and s.get("source")=="external")
        src_html = ""
        if int_sigs: src_html += f'<span class="src-int">int:{int_sigs}</span> '
        if ext_sigs: src_html += f'<span class="src-ext">ext:{ext_sigs}</span>'

        st.markdown(f"""
        <div class="pc">
            <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;">
                {ttag(prop["node_type"])}<b>{prop["node_label"]}</b> {src_html}
                <span style="font-size:.72rem;color:var(--tm);margin-left:auto;">{prop["signal_count"]} señales · conf {prop["avg_confidence"]:.2f}</span>
            </div>
            <div style="font-size:.8rem;color:var(--tm);margin-bottom:.5rem;">{prop["description"]}</div>
            {ch_html}
            <div style="font-size:.7rem;color:var(--tm);">{prop["id"]}</div>
        </div>""", unsafe_allow_html=True)

        ca,cb,cc = st.columns(3)
        with ca:
            if st.button("✓ Aprobar", key=f"ap_{prop['id']}"):
                try:
                    pq.approve(prop["id"])
                    st.session_state.graph = graph
                    st.success("Aprobado y escrito al grafo.")
                    st.rerun()
                except Exception as e: st.error(str(e))
        with cb:
            if st.button("✗ Rechazar", key=f"rj_{prop['id']}"):
                try:
                    pq.reject(prop["id"])
                    st.success("Rechazado.")
                    st.rerun()
                except Exception as e: st.error(str(e))
        with cc:
            if st.button("⟳ Diferir", key=f"df_{prop['id']}"):
                try:
                    pq.defer(prop["id"])
                    st.success("Diferido.")
                    st.rerun()
                except Exception as e: st.error(str(e))

    resolved = [p for p in pq.all() if p.get("status")!="pending"]
    if resolved:
        with st.expander(f"Historial resuelto ({len(resolved)})"):
            for p in reversed(resolved):
                sc = {"approved":"var(--gn)","rejected":"var(--rd)","deferred":"var(--yw)"}.get(p["status"],"var(--tm)")
                st.markdown(f'<div style="font-size:.78rem;padding:.4rem 0;border-bottom:1px solid var(--b);">{ttag(p["node_type"])}<b>{p["node_label"]}</b><span style="color:{sc};margin-left:.5rem;">{p["status"].upper()}</span><span style="color:var(--tm);margin-left:.5rem;font-size:.7rem;">{p.get("resolved_at","")[:10]}</span></div>', unsafe_allow_html=True)

# ============================================================
# TAB 06 — Exportar (Sprint 4)
# ============================================================
with t6:
    st.markdown("### Exportar contexto")
    st.markdown('<p style="color:var(--tm);font-size:.82rem;">El grafo como contexto portable para cualquier herramienta.</p>', unsafe_allow_html=True)

    if not graph.get_nodes():
        st.markdown('<p style="color:var(--tm);">Grafo vacío. Ingresa fuentes primero.</p>', unsafe_allow_html=True)
    else:
        exp = ContextExporter(graph)
        stats = exp.stats()

        # Stats
        st.markdown(f'<div class="mc"><div style="font-size:.7rem;color:var(--tm);margin-bottom:.5rem;">RESUMEN DEL GRAFO</div><div style="font-size:.8rem;line-height:1.8;">{" · ".join(f"<b>{t}</b>:{c}" for t,c in stats["by_type"].items())} · <b>edges</b>:{stats["total_edges"]} · <b>NM</b>:{stats["nm_graph"].get("nm","—")}</div></div>', unsafe_allow_html=True)

        c1,c2 = st.columns(2)

        with c1:
            st.markdown("**Prompt para cualquier IA**")
            prompt_text = exp.to_prompt()
            st.text_area("", value=prompt_text, height=250, key="prompt_export")
            st.download_button("⬇ Descargar prompt.txt", prompt_text, "context_prompt.txt", "text/plain", use_container_width=True)

        with c2:
            st.markdown("**Markdown estructurado**")
            md_text = exp.to_markdown()
            st.text_area("", value=md_text, height=250, key="md_export")
            st.download_button("⬇ Descargar context.md", md_text, "context.md", "text/markdown", use_container_width=True)

        st.markdown("---")
        c3,c4 = st.columns(2)

        with c3:
            st.markdown("**JSON completo**")
            inc_ev = st.checkbox("Incluir evidencia y propuestas", value=False)
            json_text = exp.to_json(include_evidence=inc_ev)
            st.download_button("⬇ Descargar graph.json", json_text, "graph_state_export.json", "application/json", use_container_width=True)

        with c4:
            st.markdown("**CSV de nodos**")
            csv_text = exp.to_csv()
            st.download_button("⬇ Descargar nodes.csv", csv_text, "nodes.csv", "text/csv", use_container_width=True)

# ============================================================
# TAB 07 — Historial
# ============================================================
with t7:
    st.markdown("### Historial de versiones")
    st.markdown('<p style="color:var(--tm);font-size:.82rem;">Cada cambio aprobado genera un commit git. El grafo completo es auditable y reversible.</p>', unsafe_allow_html=True)

    # Reset section
    st.markdown("**Resetear grafo**")
    if st.button("🗑 Borrar todos los nodos y empezar de cero", use_container_width=True):
        st.session_state.confirm_reset_tab = True
    if st.session_state.get("confirm_reset_tab"):
        st.warning("¿Segura? Esta acción no se puede deshacer desde la interfaz.")
        ca, cb = st.columns(2)
        with ca:
            if st.button("✓ Confirmar reset", key="tab_reset_yes"):
                graph._nodes = {}
                graph._edges = []
                graph._evidence = []
                graph._proposals = []
                graph.save("reset: graph cleared by user")
                st.session_state.graph = graph
                st.session_state.last_gen = None
                st.session_state.last_coh = None
                st.session_state.cycle = 0
                st.session_state.confirm_reset_tab = False
                st.success("Grafo reiniciado.")
                st.rerun()
        with cb:
            if st.button("✗ Cancelar", key="tab_reset_no"):
                st.session_state.confirm_reset_tab = False
                st.rerun()
    st.markdown("---")
    commits = graph.history()

    if not commits:
        st.markdown('<p style="color:var(--tm);">Sin historial git disponible. El sistema registrará commits automáticamente.</p>', unsafe_allow_html=True)
    else:
        for commit in commits:
            c1,c2 = st.columns([4,1])
            with c1:
                st.markdown(f'<div class="nc ns"><code style="color:var(--ac);font-size:.75rem;">{commit["hash"]}</code><span style="font-size:.82rem;margin-left:.8rem;">{commit["message"]}</span></div>', unsafe_allow_html=True)
            with c2:
                if st.button("Restaurar", key=f"rb_{commit['hash']}"):
                    try:
                        graph.rollback(commit["hash"])
                        st.session_state.graph = graph
                        st.success(f"Restaurado a {commit['hash']}")
                        st.rerun()
                    except Exception as e: st.error(str(e))
