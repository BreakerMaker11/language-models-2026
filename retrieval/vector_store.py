"""
ChromaDB vector store for HESA corpus cards.

Usage:
    from retrieval.vector_store import HealthVectorStore
    store = HealthVectorStore()
    store.add_batch(df[["doc_id", "card_text"]].to_dict("records"))
    results = store.query("opioid overdose harm reduction", n_results=5)
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


class HealthVectorStore:
    COLLECTION_NAME = "hesa_cards"

    def __init__(self, persist_dir: str = ".chromadb"):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
        self._col = self._client.get_or_create_collection(
            self.COLLECTION_NAME,
            embedding_function=self._ef,
        )

    def add(self, doc_id: str, card_text: str) -> None:
        """Add a single card. Skips if doc_id already exists."""
        if self._col.get(ids=[doc_id])["ids"]:
            return
        self._col.add(ids=[doc_id], documents=[card_text])

    def add_batch(self, records: list[dict]) -> None:
        """Add many cards at once. Each dict must have doc_id and card_text keys."""
        existing = set(self._col.get(limit=100_000)["ids"])
        new = [r for r in records if r["doc_id"] not in existing]
        if not new:
            print(f"All {len(records)} records already indexed — skipping.")
            return
        # ChromaDB max batch size is 5461; chunk if needed
        chunk_size = 500
        for i in range(0, len(new), chunk_size):
            chunk = new[i : i + chunk_size]
            self._col.add(
                ids=[r["doc_id"] for r in chunk],
                documents=[r["card_text"] for r in chunk],
            )
            print(f"  Indexed {min(i + chunk_size, len(new))}/{len(new)} cards …")

    def query(self, card_text: str, n_results: int = 5) -> list[dict]:
        """Return n_results nearest cards as list of {doc_id, card_text, distance}."""
        res = self._col.query(query_texts=[card_text], n_results=n_results)
        return [
            {"doc_id": i, "card_text": d, "distance": dist}
            for i, d, dist in zip(
                res["ids"][0], res["documents"][0], res["distances"][0]
            )
        ]

    def count(self) -> int:
        return self._col.count()
