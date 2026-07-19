"""
Week 2 — Embedding evaluation script.

Compares embedding models on domain-specific term pairs drawn from the HESA
health-policy codebook (codebook_v1_1.md). Scores close vs far pairs to validate
that a model can distinguish the 9 topic boundaries before use in RAG / clustering.

Usage:
    export OLLAMA_HOST=http://100.85.195.54:11434
    uv run python -m eval.embedding_eval

To add a third model: append a dict to MODELS below and re-run.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# ── Configurable model list ───────────────────────────────────────────────────
# backends: "ollama" | "sentence_transformers"
# Add a third model here if either model's gap < 0.2
MODELS = [
    {"name": "nomic-embed-text",  "backend": "ollama"},
    {"name": "all-MiniLM-L6-v2", "backend": "sentence_transformers"},
    {"name": "all-mpnet-base-v2", "backend": "sentence_transformers"},
]

# ── Domain pairs ──────────────────────────────────────────────────────────────
# 13 close pairs (same topic) + 7 far pairs (different topics, 5 hard boundary)
DOMAIN_PAIRS = [
    # CLOSE pairs
    {"term1": "pandemic",                   "term2": "infectious disease",      "pair_type": "close", "topic1": "public_health",     "topic2": "public_health",     "boundary_type": "easy"},
    {"term1": "opioid overdose",            "term2": "harm reduction program",  "pair_type": "close", "topic1": "public_health",     "topic2": "public_health",     "boundary_type": "easy"},
    {"term1": "pharmacare",                 "term2": "drug coverage",           "pair_type": "close", "topic1": "pharmacare",        "topic2": "pharmacare",        "boundary_type": "easy"},
    {"term1": "generic biologic drug",      "term2": "patented medicine",       "pair_type": "close", "topic1": "pharmacare",        "topic2": "pharmacare",        "boundary_type": "easy"},
    {"term1": "maternal care",              "term2": "midwifery",               "pair_type": "close", "topic1": "womens_health",     "topic2": "womens_health",     "boundary_type": "easy"},
    {"term1": "breast cancer",              "term2": "cervical cancer",         "pair_type": "close", "topic1": "womens_health",     "topic2": "womens_health",     "boundary_type": "easy"},
    {"term1": "mood disorder",              "term2": "psychiatric services",    "pair_type": "close", "topic1": "mental_health",     "topic2": "mental_health",     "boundary_type": "easy"},
    {"term1": "suicide prevention",         "term2": "depression",              "pair_type": "close", "topic1": "mental_health",     "topic2": "mental_health",     "boundary_type": "easy"},
    {"term1": "healthcare worker shortage", "term2": "clinical duties expansion","pair_type": "close", "topic1": "workforce",         "topic2": "workforce",         "boundary_type": "easy"},
    {"term1": "foreign-trained doctors",    "term2": "medical licensure",       "pair_type": "close", "topic1": "workforce",         "topic2": "workforce",         "boundary_type": "easy"},
    {"term1": "Indigenous health services", "term2": "Indigenous peoples health","pair_type": "close", "topic1": "indigenous_health", "topic2": "indigenous_health", "boundary_type": "easy"},
    {"term1": "childhood cancer treatment", "term2": "pediatric care",          "pair_type": "close", "topic1": "childrens_health",  "topic2": "childrens_health",  "boundary_type": "easy"},
    {"term1": "carcinogen",                 "term2": "cancer screening",        "pair_type": "close", "topic1": "cancer",            "topic2": "cancer",            "boundary_type": "easy"},
    # FAR pairs — easy
    {"term1": "drug coverage",              "term2": "healthcare worker shortage","pair_type": "far", "topic1": "pharmacare",        "topic2": "workforce",         "boundary_type": "easy"},
    {"term1": "pandemic",                   "term2": "maternal care",           "pair_type": "far",   "topic1": "public_health",     "topic2": "womens_health",     "boundary_type": "easy"},
    # FAR pairs — hard boundary (codebook-specific; general models may score these as close)
    {"term1": "opioid overdose",            "term2": "depression",              "pair_type": "far",   "topic1": "public_health",     "topic2": "mental_health",     "boundary_type": "hard"},
    {"term1": "harm reduction program",     "term2": "psychiatric services",    "pair_type": "far",   "topic1": "public_health",     "topic2": "mental_health",     "boundary_type": "hard"},
    {"term1": "breast cancer",              "term2": "oncology services",       "pair_type": "far",   "topic1": "womens_health",     "topic2": "cancer",            "boundary_type": "hard"},
    {"term1": "childhood cancer treatment", "term2": "cancer screening",        "pair_type": "far",   "topic1": "childrens_health",  "topic2": "cancer",            "boundary_type": "hard"},
    {"term1": "Indigenous health services", "term2": "suicide prevention",      "pair_type": "far",   "topic1": "indigenous_health", "topic2": "mental_health",     "boundary_type": "hard"},
]

# ── Embedding backends ────────────────────────────────────────────────────────

def _embed_ollama(model_name: str, texts: list[str]) -> list[np.ndarray]:
    import ollama
    resp = ollama.embed(model=model_name, input=texts)
    return [np.array(v) for v in resp.embeddings]


def _embed_st(model_name: str, texts: list[str]) -> list[np.ndarray]:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    vecs = model.encode(texts)
    return [vecs[i] for i in range(len(texts))]


def embed_pair(backend: str, model_name: str, term1: str, term2: str) -> float:
    if backend == "ollama":
        v1, v2 = _embed_ollama(model_name, [term1, term2])
    elif backend == "sentence_transformers":
        v1, v2 = _embed_st(model_name, [term1, term2])
    else:
        raise ValueError(f"Unknown backend: {backend!r}")
    return float(cosine_similarity([v1], [v2])[0][0])


# ── Gap calculation ───────────────────────────────────────────────────────────

def calculate_gap(scores: list[float], pair_types: list[str]) -> float:
    close = [s for s, t in zip(scores, pair_types) if t == "close"]
    far   = [s for s, t in zip(scores, pair_types) if t == "far"]
    if not close or not far:
        return float("nan")
    return float(np.mean(close) - np.mean(far))


# ── Console report ────────────────────────────────────────────────────────────

def _print_report(df: pd.DataFrame, model_col: str, model_name: str) -> float:
    scores      = df[model_col].tolist()
    pair_types  = df["pair_type"].tolist()
    boundaries  = df["boundary_type"].tolist()

    gap_all  = calculate_gap(scores, pair_types)

    hard_mask   = [b == "hard" for b in boundaries]
    hard_scores = [s for s, m in zip(scores, hard_mask) if m]
    hard_types  = [t for t, m in zip(pair_types, hard_mask) if m]
    gap_hard    = calculate_gap(hard_scores, hard_types)

    w = 68
    print(f"\n{'='*w}")
    print(f"  {model_name}")
    print(f"{'='*w}")
    print(f"  gap (all pairs)          : {gap_all:+.4f}  {'PASS ✓' if gap_all >= 0.2 else 'FAIL — consider a third model'}")
    print(f"  gap (hard boundary only) : {gap_hard:+.4f}")
    print(f"\n  {'pair_type':<6} {'bnd':<5} {'score':>6}  {'term1':<24} {'term2':<24}  note")
    print(f"  {'-'*62}")
    for _, row in df.iterrows():
        s     = row[model_col]
        note  = ""
        if row["pair_type"] == "close" and s < 0.5:
            note = "⚠ surprising (low)"
        if row["pair_type"] == "far"   and s > 0.6:
            note = "⚠ surprising (high)"
        bnd = "hard" if row["boundary_type"] == "hard" else "easy"
        print(f"  {row['pair_type']:<6} {bnd:<5} {s:>6.3f}  {row['term1']:<24} {row['term2']:<24}  {note}")
    print(f"{'='*w}")
    return gap_all


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    df = pd.DataFrame(DOMAIN_PAIRS)

    for m in MODELS:
        safe = m["name"].replace(":", "_").replace("-", "_").replace(".", "_")
        col  = f"score_{safe}"
        print(f"\nEmbedding with {m['name']} ({m['backend']}) …", flush=True)
        scores = []
        for _, row in df.iterrows():
            s = embed_pair(m["backend"], m["name"], row["term1"], row["term2"])
            scores.append(s)
            print(f"  {row['term1']!r} / {row['term2']!r} → {s:.3f}")
        df[col] = scores

    # Console report per model
    gaps = {}
    for m in MODELS:
        safe = m["name"].replace(":", "_").replace("-", "_").replace(".", "_")
        col  = f"score_{safe}"
        gap  = _print_report(df, col, m["name"])
        gaps[m["name"]] = gap

    # Summary
    print("\n── Gap summary ──────────────────────────────────────────")
    for name, gap in gaps.items():
        status = "PASS" if gap >= 0.2 else "FAIL"
        print(f"  {name:<28} gap={gap:+.4f}  {status}")
    if any(g < 0.2 for g in gaps.values()):
        print("\n  ⚠ At least one model gap < 0.2.")
        print("    → Visit https://huggingface.co/spaces/mteb/leaderboard")
        print("    → Filter: task=STS, language=English, params < 500M")
        print("    → Add to MODELS: {\"name\": \"<hf_id>\", \"backend\": \"sentence_transformers\"}")

    # Write CSV
    out_cols = ["term1", "term2", "pair_type", "topic1", "topic2", "boundary_type"]
    score_cols = [
        f"score_{m['name'].replace(':', '_').replace('-', '_').replace('.', '_')}"
        for m in MODELS
    ]
    out = df[out_cols + score_cols]
    Path("results").mkdir(exist_ok=True)
    out_path = Path("results/embedding_eval.csv")
    out.to_csv(out_path, index=False)
    print(f"\nWritten {out_path}  ({len(out)} rows)")


if __name__ == "__main__":
    main()
