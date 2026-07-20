"""
HESA Health-Policy Brief Explorer — Week 8 Demo App

Launch:
    export OLLAMA_HOST=http://100.85.195.54:11434
    uv run --no-sync streamlit run app/streamlit_app.py

NOTE (torch wheel): This Mac runs macOS 15 on x86_64. torch==2.11.0 (pinned in
pyproject.toml for the Linux GPU server) has no wheel for macosx_15_0_x86_64.
Use `uv run --no-sync` to skip the torch wheel check and run with the packages
that ARE installed. The app does not import torch directly; sentence-transformers
uses it for ChromaDB embeddings but Streamlit imports are lazy enough that this
works at runtime on this machine.
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Constants ─────────────────────────────────────────────────────────────────

CONFIG_PATH  = PROJECT_ROOT / "src" / "baseline_recipe_classifier" / "config.yaml"
CORPUS_PATH  = PROJECT_ROOT / "data" / "health" / "corpus.csv"
CHUNKS_PATH  = PROJECT_ROOT / "data" / "health" / "rag_chunks.jsonl"
SYNC_VERSION = PROJECT_ROOT / "data" / "health" / "SYNC_VERSION"
RESULTS_DIR  = PROJECT_ROOT / "results"
DEMO_DIR     = PROJECT_ROOT / "demo"
CHROMA_DIR   = PROJECT_ROOT / "chroma"

VALID_CODES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health",
    "other_none",
]

LABEL_COLOURS = {
    "public_health":    "#e74c3c",
    "pharmacare":       "#3498db",
    "womens_health":    "#9b59b6",
    "workforce":        "#2ecc71",
    "childrens_health": "#f39c12",
    "mental_health":    "#1abc9c",
    "cancer":           "#e67e22",
    "indigenous_health":"#27ae60",
    "other_none":       "#95a5a6",
    "PARSE_FAIL":       "#c0392b",
    "TODO":             "#bdc3c7",
}

STATUS_COLOURS = {
    "echoed":      "#3498db",
    "endorsed":    "#2ecc71",
    "committed":   "#27ae60",
    "unaddressed": "#e74c3c",
    "TODO":        "#bdc3c7",
}

# ── Cached resource loaders ───────────────────────────────────────────────────

@st.cache_resource
def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@st.cache_resource
def load_corpus_stats():
    # Card corpus (classifiable documents — all are hesa_brief)
    card_total = 0
    try:
        df = pd.read_csv(CORPUS_PATH)
        card_total = len(df)
    except Exception:
        pass

    # Chunk corpus (all three source types, from rag_chunks.jsonl)
    chunks_by_source: dict[str, int] = {}
    try:
        from collections import Counter
        counts: Counter = Counter()
        with open(CHUNKS_PATH) as f:
            import json as _json
            for line in f:
                line = line.strip()
                if line:
                    obj = _json.loads(line)
                    counts[obj.get("source_type", "unknown")] += 1
        chunks_by_source = dict(counts)
    except Exception:
        pass

    return {"card_total": card_total, "chunks_by_source": chunks_by_source}


@st.cache_resource
def load_chunk_count():
    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        ef = SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
        col = client.get_collection("hesa_chunks", embedding_function=ef)
        return col.count()
    except Exception:
        return None


@st.cache_resource
def get_chroma_collection():
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
    return client.get_collection("hesa_chunks", embedding_function=ef)


@st.cache_resource
def load_cma_sections():
    path = DEMO_DIR / "cma_sections.json"
    with open(path) as f:
        return json.load(f)


@st.cache_resource
def load_cached_classify():
    path = DEMO_DIR / "cached_classify.json"
    with open(path) as f:
        return json.load(f)


@st.cache_resource
def load_cached_ask():
    path = DEMO_DIR / "cached_ask.json"
    with open(path) as f:
        return json.load(f)


# ── Keyword classifier (simplified — approximates topic_rules.yaml) ───────────

def keyword_classify(text: str) -> str:
    """
    Lightweight keyword matcher. Approximates the corpus topic_seed rules.
    Precedence: indigenous > womens > childrens > pharmacare > public_health >
    mental_health > workforce > cancer > other_none.
    Strong keywords: one match is sufficient.
    """
    t = text.lower()

    rules = [
        ("indigenous_health", [
            "first nations", "inuit", "métis", "metis", "jordan's principle",
            "nihb", "indigenous health", "indigenous peoples health",
            "self-determination", "culturally safe",
        ]),
        ("womens_health", [
            "breast implant", "cervical cancer", "menopause", "endometriosis",
            "midwifery", "midwife", "maternal care", "reproductive health",
            "womens health", "women's health", "gender gap",
        ]),
        ("childrens_health", [
            "paediatric", "pediatric", "neonatal", "child health",
            "child development", "children's health",
        ]),
        ("pharmacare", [
            "pharmacare", "biosimilar", "patented medicine", "drug formulary",
            "drug coverage", "drug shortage", "pharmaceutical sovereignty",
            "pmprb", "drug pricing", "drug benefit",
        ]),
        ("public_health", [
            "opioid", "overdose", "toxic drug", "fentanyl", "harm reduction",
            "safe supply", "antimicrobial resistance", "amr", "pandemic",
            "vaccine program", "vaccination program", "long covid", "addiction",
        ]),
        ("mental_health", [
            "mental health", "psychiatric", "depression", "anxiety disorder",
            "suicide prevention", "mental illness",
        ]),
        ("workforce", [
            "internationally trained", "credential recognition", "licensure",
            "health worker shortage", "nurse retention", "physician burnout",
            "scope of practice", "practice-ready assessment", "residency position",
        ]),
        ("cancer", [
            "cancer screening", "oncology", "carcinogen", "breast cancer",
            "colorectal cancer", "cervical cancer screening",
        ]),
    ]

    for label, keywords in rules:
        if any(kw in t for kw in keywords):
            return label
    return "other_none"


# ── Classify via Ollama ───────────────────────────────────────────────────────

def classify_ollama(card_text: str, cfg: dict) -> dict:
    """Run gemma2:2b zero-shot classifier. Returns {prediction, elapsed_s}."""
    import ollama
    from retrieval.promptv2_classify import (
        build_prompt, health_categories, health_model,
        SYSTEM, VALID_CODES as VC,
    )
    model, temperature, num_ctx, ollama_options = health_model(cfg)
    categories = health_categories(cfg)
    prompt = build_prompt(card_text, categories)

    t0 = time.perf_counter()
    resp = ollama.generate(
        model=model,
        prompt=prompt,
        system=SYSTEM,
        options={"temperature": temperature, "num_ctx": num_ctx, **ollama_options},
        keep_alive="30m",
    )
    elapsed = time.perf_counter() - t0

    raw = resp.response.strip().lower().strip('."\'`* ')
    prediction = raw if raw in VC else None

    if prediction is None:
        for code in VC:
            if code in resp.response.lower():
                prediction = code
                break

    return {"prediction": prediction or "PARSE_FAIL", "elapsed_s": elapsed}


# ── RAG retrieval (direct, no Ollama) ────────────────────────────────────────

def retrieve_passages(col, question: str, source_type_filter: str | None, k: int) -> list[dict]:
    kwargs = dict(query_texts=[question], n_results=max(k, 5),
                  include=["metadatas", "documents", "distances"])
    if source_type_filter and source_type_filter != "All":
        kwargs["where"] = {"source_type": {"$eq": source_type_filter}}
    res = col.query(**kwargs)
    return [
        {
            "doc_id":   res["ids"][0][i],
            "text":     res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
        }
        for i in range(min(k, len(res["ids"][0])))
    ]


def generate_answer(passages: list[dict], question: str) -> str:
    import ollama

    SYSTEM_PROMPT = (
        "You are a research assistant specialising in Canadian parliamentary "
        "health-policy documents. Answer only from the provided passages. "
        "Cite [doc_id] after every claim that draws from a passage. "
        "If the passages do not contain enough information to answer, say so explicitly."
    )
    lines = ["Here are the retrieved passages:\n"]
    for p in passages:
        m = p["metadata"]
        page_sec = " / ".join(filter(None, [m.get("page_range", ""), m.get("section_title", "")]))
        label_parts = [p["doc_id"], m.get("org", ""), m.get("study_or_consultation_title", "")]
        if page_sec:
            label_parts.append(page_sec)
        label = " | ".join(x for x in label_parts if x)
        lines.append(f"[{label}]")
        lines.append(p["text"].strip())
        lines.append("")
    lines.append(f"Question: {question}")
    lines.append("\nAnswer using only the passages above. Cite [doc_id] for every factual claim. "
                 "If the passages do not contain the answer, say so.")
    prompt = "\n".join(lines)

    resp = ollama.generate(
        model="gemma2:2b",
        prompt=prompt,
        system=SYSTEM_PROMPT,
        options={"num_ctx": 8192, "temperature": 0.0},
        keep_alive="30m",
    )
    return resp.response.strip()


# ── UI helpers ────────────────────────────────────────────────────────────────

def label_badge(label: str) -> str:
    colour = LABEL_COLOURS.get(label, "#95a5a6")
    return f'<span style="background:{colour};color:white;padding:3px 10px;border-radius:12px;font-weight:600;font-size:0.85em">{label}</span>'


def status_badge(status: str) -> str:
    colour = STATUS_COLOURS.get(status.lower(), "#bdc3c7")
    return f'<span style="background:{colour};color:white;padding:3px 10px;border-radius:12px;font-weight:600;font-size:0.85em">{status.upper()}</span>'


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.title("HESA Policy Explorer")
        st.caption("Canadian parliamentary health-policy briefs · Standing Committee on Health")

        st.divider()
        st.subheader("Corpus")

        stats = load_corpus_stats()
        st.metric("Classifiable cards (corpus.csv)", stats["card_total"])

        chunk_count = load_chunk_count()
        if chunk_count is not None:
            st.metric("Chunks indexed (ChromaDB)", chunk_count)
            for src, n in sorted(stats["chunks_by_source"].items()):
                st.write(f"  `{src}`: {n}")
        else:
            st.warning("ChromaDB index not found — run `uv run python -m rag.build_index`")

        st.divider()
        st.subheader("Models")
        st.write("**Generation:** gemma2:2b (Ollama)")
        st.write("**Embeddings:** all-MiniLM-L6-v2 (local CPU)")
        ollama_host = os.environ.get("OLLAMA_HOST", "not set")
        st.caption(f"OLLAMA_HOST: `{ollama_host}`")

        st.divider()
        st.subheader("Corpus version")
        if SYNC_VERSION.exists():
            st.code(SYNC_VERSION.read_text().strip(), language=None)
        else:
            st.caption("SYNC_VERSION not found in data/health/")


# ── Tab 1: Classify ───────────────────────────────────────────────────────────

def render_tab_classify():
    st.header("Classify a document")
    st.caption(
        "Select a CMA section or paste your own text. "
        "Two classifiers run in parallel: keyword rules (fast, no GPU) and "
        "gemma2:2b zero-shot (requires OLLAMA_HOST)."
    )

    sections_data = load_cma_sections()
    sections = sections_data["sections"]
    section_labels = [f"{s['title']}" for s in sections] + ["(paste your own)"]

    selected_label = st.selectbox("Demo document", section_labels, index=0)
    custom_mode = selected_label == "(paste your own)"

    if custom_mode:
        card_text = st.text_area(
            "Paste document text (title + body)",
            height=200,
            placeholder="Paste the first ~250 words of a health-policy brief here…",
        )
        section_id = None
    else:
        section = next(s for s in sections if s["title"] == selected_label)
        section_id = section["section_id"]
        card_text = section["card_text"]
        with st.expander("Document text", expanded=False):
            st.write(card_text)

    if st.button("Classify", type="primary") and card_text.strip():
        # ── Keyword prediction (always fast) ──────────────────────────────────
        kw_pred = keyword_classify(card_text)

        # ── Gemma4 prediction ─────────────────────────────────────────────────
        cfg = load_config()
        cached = load_cached_classify()
        gemma4_result = None
        offline = False

        try:
            with st.spinner("Running gemma2:2b…"):
                gemma4_result = classify_ollama(card_text, cfg)
        except Exception as e:
            offline = True
            if section_id and section_id in cached:
                gemma4_result = cached[section_id]
            else:
                gemma4_result = {"prediction": "PARSE_FAIL", "elapsed_s": 0.0}

        # ── Display ───────────────────────────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Keyword rules")
            st.markdown(label_badge(kw_pred), unsafe_allow_html=True)
            st.caption("Simplified keyword matcher (approximates topic_rules.yaml)")

        with col2:
            st.subheader("gemma2:2b zero-shot")
            pred = gemma4_result["prediction"]
            st.markdown(label_badge(pred), unsafe_allow_html=True)
            if offline:
                st.caption(f"⚠️ Offline result (Ollama unreachable) — cached prediction")
            else:
                st.caption(f"Elapsed: {gemma4_result['elapsed_s']:.1f}s")

        if kw_pred != gemma4_result["prediction"]:
            st.info(
                f"Methods disagree: keyword→**{kw_pred}**, gemma4→**{gemma4_result['prediction']}**. "
                "This often happens on multi-topic documents or when keyword coverage is sparse."
            )


# ── Tab 2: Ask the record ─────────────────────────────────────────────────────

def render_tab_ask():
    st.header("Ask the record")
    st.caption(
        "Ask a policy question. The app retrieves relevant passages from the HESA corpus "
        "and asks gemma2:2b to answer using only those passages, with [doc_id] citations."
    )

    question = st.text_input(
        "Question",
        placeholder="e.g. What did the committee recommend on breast cancer screening?",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        filter_display = st.selectbox(
            "Source filter",
            ["All", "hesa_brief", "hesa_report", "gov_response"],
            index=0,
            help="Restrict retrieval to one document role in the policy pipeline.",
        )
    with col2:
        k = st.slider("Passages (k)", min_value=1, max_value=5, value=3)

    source_filter = None if filter_display == "All" else filter_display

    if st.button("Ask", type="primary") and question.strip():
        cached_ask = load_cached_ask()
        offline = False
        answer = None
        passages = []

        try:
            col = get_chroma_collection()
            with st.spinner("Retrieving passages…"):
                passages = retrieve_passages(col, question, source_filter, k)

            with st.spinner("Generating answer with gemma2:2b…"):
                answer = generate_answer(passages, question)

        except Exception as e:
            offline = True
            answer = cached_ask["answer"]
            passages = cached_ask["passages"]

        if offline:
            st.warning("⚠️ Offline result — Ollama unreachable. Showing cached example answer.")

        st.subheader("Answer")
        st.markdown(answer)

        st.divider()
        st.subheader(f"Retrieved passages ({len(passages)})")

        for i, p in enumerate(passages, 1):
            m = p["metadata"]
            page_sec = " / ".join(filter(None, [
                m.get("page_range", ""), m.get("section_title", "")
            ]))
            expander_label = f"[{i}] {m.get('org', p['doc_id'])} — {m.get('study_or_consultation_title', '')[:60]}"
            with st.expander(expander_label, expanded=(i == 1)):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**org:** {m.get('org', '—')}")
                    st.write(f"**study:** {m.get('study_or_consultation_title', '—')}")
                    if page_sec:
                        st.write(f"**page/§:** {page_sec}")
                with col2:
                    st.write(f"**doc_id:** `{p['doc_id']}`")
                    st.write(f"**distance:** {p['distance']:.4f}")
                    src_url = m.get("source_url", "")
                    if src_url:
                        st.markdown(f"[Source document ↗]({src_url})")

                st.write("**Passage text:**")
                st.write(p["text"])


# ── Tab 3: Evaluation ─────────────────────────────────────────────────────────

def render_tab_eval():
    st.header("Classifier evaluation")
    st.caption(
        "All results are pre-computed and read from `results/eval_summary_*.json`. "
        "Gold set: 217 hand-labelled HESA documents (frozen — never trained or tuned against)."
    )

    # Load all eval_summary files
    rows = []
    for path in sorted(RESULTS_DIR.glob("eval_summary_*.json")):
        try:
            d = json.loads(path.read_text())
            pc = d.get("per_class", {})
            on_recall = pc.get("other_none", {}).get("r", None)
            eff = d.get("efficiency") or {}
            rows.append({
                "method":              d.get("method", path.stem),
                "accuracy":            d.get("accuracy"),
                "macro_f1_all":        d.get("macro_f1_all"),
                "macro_f1_support10":  d.get("macro_f1_support10"),
                "other_none_recall":   on_recall,
                "median_latency_s":    eff.get("median_latency_s"),
            })
        except Exception:
            continue

    if not rows:
        st.error("No eval_summary_*.json files found in results/.")
        return

    df = pd.DataFrame(rows).sort_values("accuracy", ascending=False).reset_index(drop=True)

    st.subheader("Method comparison")
    st.dataframe(
        df.style.format({
            "accuracy":           "{:.3f}",
            "macro_f1_all":       "{:.3f}",
            "macro_f1_support10": "{:.3f}",
            "other_none_recall":  lambda x: f"{x:.3f}" if x is not None else "—",
            "median_latency_s":   lambda x: f"{x:.1f}s" if x is not None else "—",
        }),
        width="stretch",
        hide_index=True,
    )

    # Bar chart of macro_f1_support10
    st.subheader("Macro-F1 (support ≥ 10 classes)")
    chart_df = df[["method", "macro_f1_support10"]].dropna().set_index("method")
    st.bar_chart(chart_df)

    # Confusion matrix image
    st.subheader("Confusion matrix — gemma2:2b zero-shot")
    cm_path = RESULTS_DIR / "confusion_zeroshot_gemma4-12b.png"
    if cm_path.exists():
        st.image(str(cm_path), width="stretch")
    else:
        st.caption("confusion_zeroshot_gemma4-12b.png not found in results/")

    st.info(
        "**Reading the table:** `macro_f1_support10` excludes classes with fewer than 10 gold "
        "examples (drops `indigenous_health` n=3). `other_none_recall` shows how often "
        "civil-liberties/individual-grievance documents are correctly identified. "
        "Methods without latency data (weakrules, embed_lr) run entirely on CPU."
    )


# ── Tab 4: Gap analysis ───────────────────────────────────────────────────────

def render_tab_gap():
    st.header("Gap analysis — CMA ministerial letter")
    st.caption(
        "Eight policy asks from the CMA letter cross-referenced against the HESA corpus: "
        "what stakeholders asked for (briefs), what the committee recommended (reports), "
        "and what the government committed to (responses). "
        "Run `uv run python scripts/precompute_gap.py` to generate this data."
    )

    gap_path = RESULTS_DIR / "gap_analysis.json"
    if not gap_path.exists():
        st.warning(
            "**results/gap_analysis.json not found.**\n\n"
            "Generate it first:\n"
            "```\nexport OLLAMA_HOST=http://100.85.195.54:11434\n"
            "uv run --no-sync python scripts/precompute_gap.py\n```"
        )
        return

    try:
        gap_data = json.loads(gap_path.read_text())
    except Exception as e:
        st.error(f"Could not parse gap_analysis.json: {e}")
        return

    sections = gap_data.get("sections", [])
    if not sections:
        st.error("gap_analysis.json has no sections.")
        return

    section_titles = [s["title"] for s in sections]
    selected_title = st.selectbox("CMA section", section_titles)
    section = next(s for s in sections if s["title"] == selected_title)

    st.subheader(section["title"])
    st.write(f"**Ask:** {section['ask_text']}")
    st.divider()

    layers = [
        ("hesa_brief",   "Stakeholder briefs"),
        ("hesa_report",  "Committee recommendations"),
        ("gov_response", "Government responses"),
    ]

    cols = st.columns(3)
    for col, (src_type, layer_label) in zip(cols, layers):
        layer = section.get("layers", {}).get(src_type, {})
        status = layer.get("status", "TODO")

        with col:
            st.markdown(f"**{layer_label}**")
            st.markdown(status_badge(status), unsafe_allow_html=True)
            st.write("")

            answer = layer.get("answer", "")
            if answer:
                st.write(answer[:500] + ("…" if len(answer) > 500 else ""))

            passages = layer.get("passages", [])
            for p in passages:
                m = p.get("metadata", {})
                org = m.get("org", p.get("doc_id", ""))
                src_url = m.get("source_url", "")
                snippet = p.get("text", "")[:150].strip()
                if src_url:
                    st.markdown(f"**[{org}]({src_url})**")
                else:
                    st.markdown(f"**{org}**")
                st.caption(snippet + "…")
                st.write("")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="HESA Policy Explorer",
        page_icon="🏛️",
        layout="wide",
    )

    render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Classify",
        "Ask the record",
        "Evaluation",
        "Gap analysis",
    ])

    with tab1:
        render_tab_classify()
    with tab2:
        render_tab_ask()
    with tab3:
        render_tab_eval()
    with tab4:
        render_tab_gap()


if __name__ == "__main__":
    main()
