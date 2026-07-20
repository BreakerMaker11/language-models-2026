"""
RAG question-answering over the HESA chunk index.

ask(question, source_type_filter=None, k=3):
  - Embeds question with all-MiniLM-L6-v2
  - Queries ChromaDB (n_results=5), takes top k
  - Builds grounded prompt → gemma4:12b via Ollama (no num_predict cap)
  - Returns answer text

CLI:
    export OLLAMA_HOST=http://100.85.195.54:11434
    uv run python -m rag.ask "your question" [--filter hesa_brief|hesa_report|gov_response] [--k 3]
"""

import argparse
import os
import sys
from pathlib import Path

import chromadb
import ollama
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = PROJECT_ROOT / "chroma"
COLLECTION_NAME = "hesa_chunks"
EMBED_MODEL = "all-MiniLM-L6-v2"
GENERATION_MODEL = "gemma2:2b"
NUM_CTX = 16384  # generation needs more room than classification

SYSTEM_PROMPT = (
    "You are a research assistant specialising in Canadian parliamentary "
    "health-policy documents. Answer only from the provided passages. "
    "Cite [doc_id] after every claim that draws from a passage. "
    "If the passages do not contain enough information to answer, say so explicitly."
)

VALID_FILTERS = {"hesa_brief", "hesa_report", "gov_response"}


def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = SentenceTransformerEmbeddingFunction(EMBED_MODEL)
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


def _build_prompt(question: str, passages: list[dict]) -> str:
    lines = ["Here are the retrieved passages:\n"]
    for p in passages:
        m = p["metadata"]
        label_parts = [p["doc_id"], m.get("org", ""), m.get("study_or_consultation_title", "")]
        page_sec = " / ".join(filter(None, [m.get("page_range", ""), m.get("section_title", "")]))
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
    return "\n".join(lines)


def ask(
    question: str,
    source_type_filter: str | None = None,
    k: int = 3,
) -> tuple[str, list[dict]]:
    """
    Retrieve relevant passages and generate a grounded answer.

    Args:
        question: Natural language question.
        source_type_filter: One of 'hesa_brief', 'hesa_report', 'gov_response', or None.
        k: Number of passages to include in the prompt (top-k of n_results=5).

    Returns:
        (answer, passages) — answer is the model response; passages is the list
        of retrieved chunks (each has doc_id, text, metadata, distance).
        Retrieval runs once; passages are returned so callers can display them
        without a second round-trip to ChromaDB.
    """
    if source_type_filter and source_type_filter not in VALID_FILTERS:
        raise ValueError(f"source_type_filter must be one of {VALID_FILTERS} or None")

    col = _get_collection()

    query_kwargs = dict(query_texts=[question], n_results=5)
    if source_type_filter:
        query_kwargs["where"] = {"source_type": {"$eq": source_type_filter}}

    results = col.query(**query_kwargs)

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    passages = [
        {"doc_id": ids[i], "text": documents[i], "metadata": metadatas[i], "distance": distances[i]}
        for i in range(min(k, len(ids)))
    ]

    prompt = _build_prompt(question, passages)

    resp = ollama.generate(
        model=GENERATION_MODEL,
        prompt=prompt,
        system=SYSTEM_PROMPT,
        options={"num_ctx": NUM_CTX, "temperature": 0.0},
        keep_alive="30m",
    )
    return resp.response.strip(), passages


def _print_passages(passages: list[dict]) -> None:
    print(f"\n{'─'*60}")
    print(f"Retrieved {len(passages)} passage(s):")
    print(f"{'─'*60}")
    for i, p in enumerate(passages, 1):
        m = p["metadata"]
        print(f"\n[{i}] doc_id:  {p['doc_id']}")
        print(f"    org:     {m.get('org', '')}")
        print(f"    study:   {m.get('study_or_consultation_title', '')}")
        page_sec = " / ".join(filter(None, [m.get("page_range", ""), m.get("section_title", "")]))
        if page_sec:
            print(f"    page/§:  {page_sec}")
        print(f"    dist:    {p['distance']:.4f}")
        print(f"    text:    {p['text'][:300].strip()} …")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask a question over the HESA chunk index."
    )
    parser.add_argument("question", help="Question to answer")
    parser.add_argument(
        "--filter",
        dest="source_type_filter",
        choices=list(VALID_FILTERS),
        default=None,
        help="Restrict retrieval to this source type",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of passages to include in the prompt (default: 3)",
    )
    args = parser.parse_args()

    # Ensure OLLAMA_HOST is set; warn if using default
    if not os.environ.get("OLLAMA_HOST"):
        print(
            "WARNING: OLLAMA_HOST not set. "
            "Set it with: export OLLAMA_HOST=http://100.85.195.54:11434",
            file=sys.stderr,
        )

    col = _get_collection()
    query_kwargs = dict(query_texts=[args.question], n_results=5)
    if args.source_type_filter:
        query_kwargs["where"] = {"source_type": {"$eq": args.source_type_filter}}

    results = col.query(**query_kwargs)
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    passages = [
        {"doc_id": ids[i], "text": documents[i], "metadata": metadatas[i], "distance": distances[i]}
        for i in range(min(args.k, len(ids)))
    ]

    _print_passages(passages)

    filter_label = args.source_type_filter or "all"
    print(f"\n{'─'*60}")
    print(f"Question: {args.question}")
    print(f"Filter:   {filter_label}  |  k={args.k}  |  model={GENERATION_MODEL}")
    print(f"{'─'*60}\n")

    answer, _ = ask(args.question, source_type_filter=args.source_type_filter, k=args.k)
    print("Answer:")
    print(answer)
    print(f"\n{'─'*60}")


if __name__ == "__main__":
    main()
