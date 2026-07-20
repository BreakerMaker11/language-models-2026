"""
RAG evaluation: retrieval hit-rate and generation faithfulness.

Metrics
-------
hit@k        — at least one expected doc_id appears in the top-k retrieved chunks
citation_valid — every [doc_id] cited in the answer was present in the retrieved passages

Usage:
    export OLLAMA_HOST=http://100.85.195.54:11434
    uv run python -m rag.eval                        # retrieval + generation
    uv run python -m rag.eval --retrieval-only        # skip LLM, fast
    uv run python -m rag.eval --queries rag/eval_queries.yaml
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import yaml
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = PROJECT_ROOT / "chroma"
COLLECTION_NAME = "hesa_chunks"
EMBED_MODEL = "all-MiniLM-L6-v2"
QUERIES_PATH = PROJECT_ROOT / "rag" / "eval_queries.yaml"
RESULTS_DIR = PROJECT_ROOT / "results"

K_VALUES = [3, 5]   # hit-rate evaluated at both thresholds


# ── ChromaDB ──────────────────────────────────────────────────────────────────

def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = SentenceTransformerEmbeddingFunction(EMBED_MODEL)
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(col, query: str, source_type_filter: str | None, n_results: int = 5) -> list[dict]:
    kwargs = dict(query_texts=[query], n_results=n_results, include=["metadatas", "documents", "distances"])
    if source_type_filter:
        kwargs["where"] = {"source_type": {"$eq": source_type_filter}}
    res = col.query(**kwargs)
    return [
        {
            "chunk_id": res["ids"][0][i],
            "doc_id":   res["metadatas"][0][i].get("doc_id", ""),
            "org":      res["metadatas"][0][i].get("org", ""),
            "study":    res["metadatas"][0][i].get("study_or_consultation_title", ""),
            "text":     res["documents"][0][i],
            "distance": res["distances"][0][i],
        }
        for i in range(len(res["ids"][0]))
    ]


# ── Hit-rate ──────────────────────────────────────────────────────────────────

def hit_at_k(results: list[dict], expected_doc_ids: list[str], k: int) -> bool:
    retrieved_doc_ids = {r["doc_id"] for r in results[:k]}
    return bool(retrieved_doc_ids & set(expected_doc_ids))


# ── Citation validity ─────────────────────────────────────────────────────────

_DOC_ID_RE = re.compile(r"\[([a-z0-9_]+)\]")

def check_citations(answer: str, retrieved: list[dict]) -> dict:
    """
    Parse all [doc_id] tokens from the answer.
    Valid  = cited id matches a retrieved chunk_id or doc_id.
    Invalid = cited id was not in the retrieved set (hallucinated reference).
    """
    cited = set(_DOC_ID_RE.findall(answer))
    valid_ids = {r["chunk_id"] for r in retrieved} | {r["doc_id"] for r in retrieved}

    valid   = cited & valid_ids
    invalid = cited - valid_ids
    return {
        "cited": sorted(cited),
        "valid": sorted(valid),
        "invalid": sorted(invalid),
        "all_valid": len(invalid) == 0 and len(cited) > 0,
        "no_citations": len(cited) == 0,
    }


# ── Generation ────────────────────────────────────────────────────────────────

def generate_answer(question: str, passages: list[dict]) -> str:
    # Import lazily so --retrieval-only skips loading ollama entirely
    import ollama

    SYSTEM = (
        "You are a research assistant specialising in Canadian parliamentary "
        "health-policy documents. Answer only from the provided passages. "
        "Cite [doc_id] after every claim that draws from a passage. "
        "If the passages do not contain enough information to answer, say so explicitly."
    )

    lines = ["Here are the retrieved passages:\n"]
    for p in passages:
        page_sec = " / ".join(filter(None, [
            p.get("page_range", ""), p.get("section_title", "")
        ]))
        label_parts = [p["doc_id"], p["org"], p["study"]]
        if page_sec:
            label_parts.append(page_sec)
        label = " | ".join(x for x in label_parts if x)
        lines.append(f"[{label}]")
        lines.append(p["text"].strip())
        lines.append("")

    lines.append(f"Question: {question}")
    lines.append(
        "\nAnswer using only the passages above. "
        "Cite [doc_id] for every factual claim. "
        "If the passages do not contain the answer, say so."
    )
    prompt = "\n".join(lines)

    resp = ollama.generate(
        model="gemma4:12b",
        prompt=prompt,
        system=SYSTEM,
        options={"num_ctx": 16384, "temperature": 0.0},
        keep_alive="30m",
    )
    return resp.response.strip()


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_row(q: dict, result: dict) -> None:
    hits = " ".join(
        f"hit@{k}={'Y' if result[f'hit@{k}'] else 'N'}" for k in K_VALUES
    )
    cit = result.get("citation", {})
    if cit:
        cit_str = f"  citations={'OK' if cit['all_valid'] else ('NONE' if cit['no_citations'] else 'BAD')}"
        if cit["invalid"]:
            cit_str += f" invalid={cit['invalid']}"
    else:
        cit_str = ""
    print(f"  [{q['id']}] {hits}{cit_str}")
    print(f"         {q['description']}")
    retrieved_docs = [r["doc_id"] for r in result["retrieved"]]
    print(f"         retrieved: {retrieved_docs}")
    if not result["hit@3"]:
        print(f"         expected:  {q['hit_doc_ids']}")


def print_summary(results: list[dict], queries: list[dict], retrieval_only: bool) -> None:
    n = len(results)
    print(f"\n{'═'*60}")
    print(f"SUMMARY  ({n} queries)")
    print(f"{'─'*60}")
    for k in K_VALUES:
        hits = sum(1 for r in results if r[f"hit@{k}"])
        print(f"  hit-rate@{k}: {hits}/{n} = {hits/n:.0%}")

    if not retrieval_only:
        cits = [r["citation"] for r in results if r.get("citation")]
        if cits:
            n_ok    = sum(1 for c in cits if c["all_valid"])
            n_none  = sum(1 for c in cits if c["no_citations"])
            n_bad   = sum(1 for c in cits if c["invalid"])
            print(f"  citation valid:  {n_ok}/{len(cits)}")
            print(f"  citation none:   {n_none}/{len(cits)}  (answer but no [doc_id]s)")
            print(f"  citation bad:    {n_bad}/{len(cits)}  (hallucinated doc_ids)")
    print(f"{'═'*60}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval and generation.")
    parser.add_argument("--queries", default=str(QUERIES_PATH),
                        help=f"Path to eval queries YAML (default: {QUERIES_PATH})")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Skip LLM generation; evaluate retrieval only")
    parser.add_argument("--k", type=int, nargs="+", default=K_VALUES,
                        help="k values for hit-rate (default: 3 5)")
    args = parser.parse_args()

    if not os.environ.get("OLLAMA_HOST") and not args.retrieval_only:
        print(
            "WARNING: OLLAMA_HOST not set. "
            "Set it with: export OLLAMA_HOST=http://100.85.195.54:11434",
            file=sys.stderr,
        )

    queries_path = Path(args.queries)
    if not queries_path.exists():
        print(f"ERROR: queries file not found: {queries_path}", file=sys.stderr)
        sys.exit(1)

    with open(queries_path) as f:
        spec = yaml.safe_load(f)
    queries = spec["queries"]
    print(f"Loaded {len(queries)} queries from {queries_path.name}\n")

    col = get_collection()
    all_results = []

    for q in queries:
        print(f"[{q['id']}] {q['query']!r}  filter={q.get('filter')}")

        retrieved = retrieve(col, q["query"], q.get("filter"), n_results=max(args.k or K_VALUES))

        result = {
            "id":          q["id"],
            "query":       q["query"],
            "filter":      q.get("filter"),
            "retrieved":   [{"chunk_id": r["chunk_id"], "doc_id": r["doc_id"],
                             "org": r["org"], "distance": round(r["distance"], 4)}
                            for r in retrieved],
        }
        for k in args.k or K_VALUES:
            result[f"hit@{k}"] = hit_at_k(retrieved, q["hit_doc_ids"], k)

        if not args.retrieval_only:
            top3 = retrieved[:3]
            answer = generate_answer(q["query"], top3)
            result["answer"] = answer
            result["citation"] = check_citations(answer, top3)

        print_row(q, result)
        all_results.append(result)

    print_summary(all_results, queries, args.retrieval_only)

    # Save to results/
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    mode = "retrieval_only" if args.retrieval_only else "full"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = RESULTS_DIR / f"eval_rag_{mode}_{ts}.json"
    payload = {
        "timestamp": ts,
        "mode": mode,
        "n_queries": len(queries),
        "hit_rate": {
            f"@{k}": sum(1 for r in all_results if r[f"hit@{k}"]) / len(all_results)
            for k in (args.k or K_VALUES)
        },
        "results": all_results,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Results saved → {out_path}")


if __name__ == "__main__":
    main()
