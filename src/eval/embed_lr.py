"""
Encode train.csv card_text with all-MiniLM-L6-v2, fit LogisticRegression,
predict gold_test, write results/predictions_embed_lr_gold.csv.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from sklearn.linear_model import LogisticRegression
from sentence_transformers import SentenceTransformer

TRAIN_PATH = Path("data/health/train.csv")
GOLD_PATH = Path("data/health/gold_test.csv")
OUT_PATH = Path("results/predictions_embed_lr_gold.csv")
MODEL_NAME = "all-MiniLM-L6-v2"

STANDARD_COLS = [
    "doc_id", "true_label", "predicted_label", "raw_output",
    "parse_method", "parse_candidates", "method", "model",
    "timestamp", "prompt_tokens", "output_tokens",
    "total_duration_ms", "load_duration_ms",
]


def main():
    train = pd.read_csv(TRAIN_PATH)
    train = train[train["topic_seed"] != "unlabeled"].copy()
    print(f"Training on {len(train)} labelled rows (topic_seed != unlabeled)")

    gold = pd.read_csv(GOLD_PATH)

    print(f"Loading {MODEL_NAME} ...")
    encoder = SentenceTransformer(MODEL_NAME)

    print("Encoding train ...")
    X_train = encoder.encode(train["card_text"].tolist(), show_progress_bar=True, batch_size=32)
    y_train = train["topic_seed"].tolist()

    print("Encoding gold ...")
    X_gold = encoder.encode(gold["card_text"].tolist(), show_progress_bar=True, batch_size=32)

    print("Fitting LogisticRegression ...")
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_gold).tolist()

    ts = datetime.now(timezone.utc).isoformat()
    out = pd.DataFrame({
        "doc_id": gold["doc_id"],
        "true_label": gold["gold_topic"],
        "predicted_label": y_pred,
        "raw_output": y_pred,
        "parse_method": "lr_predict",
        "parse_candidates": None,
        "method": "embed_lr",
        "model": MODEL_NAME,
        "timestamp": ts,
        "prompt_tokens": None,
        "output_tokens": None,
        "total_duration_ms": None,
        "load_duration_ms": None,
    })[STANDARD_COLS]

    Path("results").mkdir(exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"Written {OUT_PATH}  ({len(out)} rows)")


if __name__ == "__main__":
    main()
