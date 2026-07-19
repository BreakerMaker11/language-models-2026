"""
Generate results/predictions_weakrules_gold.csv by joining corpus.csv topic_seed
onto gold_test doc_ids. topic_seed='unlabeled' → 'PARSE_FAIL'.
No inference; schema matches the standard predictions format.
"""

import pandas as pd
from pathlib import Path

GOLD_PATH = Path("data/health/gold_test.csv")
CORPUS_PATH = Path("data/health/corpus.csv")
OUT_PATH = Path("results/predictions_weakrules_gold.csv")

STANDARD_COLS = [
    "doc_id", "true_label", "predicted_label", "raw_output",
    "parse_method", "parse_candidates", "method", "model",
    "timestamp", "prompt_tokens", "output_tokens",
    "total_duration_ms", "load_duration_ms",
]


def main():
    gold = pd.read_csv(GOLD_PATH)[["doc_id", "gold_topic"]]
    corpus = pd.read_csv(CORPUS_PATH)[["doc_id", "topic_seed"]]

    merged = gold.merge(corpus[["doc_id", "topic_seed"]], on="doc_id", how="left")

    def _map_seed(v):
        if pd.isna(v) or str(v).strip() == "unlabeled":
            return "PARSE_FAIL"
        return str(v).strip()

    merged["predicted_label"] = merged["topic_seed"].apply(_map_seed)
    merged["parse_method"] = merged["topic_seed"].apply(
        lambda v: "failed" if (pd.isna(v) or str(v).strip() == "unlabeled") else "keyword_rule"
    )
    merged["true_label"] = merged["gold_topic"]
    merged["raw_output"] = merged["topic_seed"]
    merged["parse_candidates"] = None
    merged["method"] = "weakrules"
    merged["model"] = None
    merged["timestamp"] = None
    merged["prompt_tokens"] = None
    merged["output_tokens"] = None
    merged["total_duration_ms"] = None
    merged["load_duration_ms"] = None

    out = merged[STANDARD_COLS]
    assert len(out) == 217, f"Expected 217 rows, got {len(out)}"

    Path("results").mkdir(exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    n_fail = (out["predicted_label"] == "PARSE_FAIL").sum()
    print(f"Written {OUT_PATH}  ({len(out)} rows, {n_fail} PARSE_FAIL)")


if __name__ == "__main__":
    main()
