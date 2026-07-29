"""
Build a persistent ChromaDB index from data/health/rag_chunks.jsonl.

Idempotent: drops and recreates the collection on every run.
Embedder: all-MiniLM-L6-v2 (must match rag/ask.py).

Usage:
    uv run python -m rag.build_index
"""

import json
import sys
from collections import Counter
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

PROJECT_ROOT = Path(__file__).parent.parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "health" / "rag_chunks.jsonl"
CHROMA_DIR = PROJECT_ROOT / "chroma"
COLLECTION_NAME = "hesa_chunks"
EMBED_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 500

# Metadata fields stored alongside each chunk (text is the document body)
META_FIELDS = [
    "doc_id", "source_type", "org", "stakeholder_type",
    "study_or_consultation_title", "parliament_session",
    "page_range", "section_title", "recommendation_number", "source_url",
]


def load_chunks(path: Path) -> list[dict]:
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def build(chunks_path: Path = CHUNKS_PATH, chroma_dir: Path = CHROMA_DIR) -> None:
    chunks = load_chunks(chunks_path)
    print(f"Loaded {len(chunks)} chunks from {chunks_path.name}")

    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    ef = SentenceTransformerEmbeddingFunction(EMBED_MODEL)

    # Drop and recreate for a clean rebuild
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Dropped existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    col = client.create_collection(COLLECTION_NAME, embedding_function=ef)
    print(f"Created collection '{COLLECTION_NAME}' — embedding {len(chunks)} chunks …")

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        ids = [c["chunk_id"] for c in batch]
        documents = [c["text"] for c in batch]
        metadatas = []
        for c in batch:
            meta = {k: (c.get(k) or "") for k in META_FIELDS}
            # ChromaDB requires string/int/float — coerce None recommendation_number
            if meta["recommendation_number"] is None or meta["recommendation_number"] == "":
                meta["recommendation_number"] = ""
            else:
                meta["recommendation_number"] = str(meta["recommendation_number"])
            metadatas.append(meta)

        col.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  Indexed {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}")

    # Report per source_type
    counts = Counter(c["source_type"] for c in chunks)
    print(f"\nCollection '{COLLECTION_NAME}': {col.count()} chunks total")
    for src_type, n in sorted(counts.items()):
        print(f"  {src_type}: {n}")


if __name__ == "__main__":
    build()
