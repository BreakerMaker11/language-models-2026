#!/usr/bin/env python3
"""
Evaluation harness for HESA health-policy brief classifiers.

Reads a predictions CSV produced by main.py (or any method that writes the
standard schema) and writes results/eval_summary_{method}.json.

Usage:
  uv run --no-sync python evaluate_health.py results/predictions_baseline_dev.csv
  uv run --no-sync python evaluate_health.py results/predictions_baseline_dev.csv --gold data/health/gold_test.csv
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

RESULTS_DIR = Path(__file__).parent / "results"

VALID_CODES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health",
    "other_none",
]

# Classes with enough gold support to be "trainable" (heuristic: support >= 10 in gold)
TRAINABLE_CLASSES = [
    "public_health", "pharmacare", "womens_health", "workforce", "other_none",
]


def load_predictions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"doc_id", "true_label", "predicted_label", "method", "model"}
    missing = required - set(df.columns)
    if missing:
        print(f"Error: predictions file missing columns: {missing}", file=sys.stderr)
        sys.exit(1)
    return df


def compute_latency_metrics(df: pd.DataFrame) -> dict:
    """Compute median latency and throughput from Ollama duration columns (may be null)."""
    metrics = {}

    total_ms = df["total_duration_ms"].dropna() if "total_duration_ms" in df.columns else pd.Series(dtype=float)
    if not total_ms.empty:
        median_latency_s = (total_ms.median() / 1000)
        metrics["median_latency_s"] = round(median_latency_s, 3)
        metrics["throughput_cards_per_min"] = round(60 / median_latency_s, 2) if median_latency_s > 0 else None
    else:
        metrics["median_latency_s"] = None
        metrics["throughput_cards_per_min"] = None

    for col, key in [("prompt_tokens", "median_prompt_tokens"),
                     ("output_tokens", "median_output_tokens")]:
        series = df[col].dropna() if col in df.columns else pd.Series(dtype=float)
        metrics[key] = int(series.median()) if not series.empty else None

    # tokens_per_second and tokens_per_classification require both token counts and duration
    if "prompt_tokens" in df.columns and "output_tokens" in df.columns and "total_duration_ms" in df.columns:
        sub = df[["prompt_tokens", "output_tokens", "total_duration_ms"]].dropna()
        if not sub.empty:
            total_tokens = sub["prompt_tokens"] + sub["output_tokens"]
            total_s = sub["total_duration_ms"] / 1000
            metrics["tokens_per_second"] = round((total_tokens / total_s).median(), 1)
            metrics["tokens_per_classification"] = int(total_tokens.median())
        else:
            metrics["tokens_per_second"] = None
            metrics["tokens_per_classification"] = None
    else:
        metrics["tokens_per_second"] = None
        metrics["tokens_per_classification"] = None

    return metrics


def compute_classification_metrics(y_true, y_pred, label_set: list, tag: str) -> dict:
    """Per-class + macro-F1 over label_set, excluding rows where true not in label_set."""
    mask = y_true.isin(label_set)
    yt = y_true[mask]
    yp = y_pred[mask]
    if yt.empty:
        return {}

    p, r, f, s = precision_recall_fscore_support(
        yt, yp, labels=label_set, zero_division=0
    )
    per_class = {
        code: {
            "precision": round(float(p[i]), 4),
            "recall": round(float(r[i]), 4),
            "f1": round(float(f[i]), 4),
            "support": int(s[i]),
        }
        for i, code in enumerate(label_set)
    }
    macro_f1 = round(float(f1_score(yt, yp, labels=label_set, average="macro", zero_division=0)), 4)
    accuracy = round(float((yt == yp).mean()), 4)

    return {
        f"per_class_{tag}": per_class,
        f"macro_f1_{tag}": macro_f1,
        f"accuracy_{tag}": accuracy,
        f"n_{tag}": int(len(yt)),
    }


def run_eval(predictions_path: Path, gold_path: Path | None = None):
    df = load_predictions(predictions_path)

    method = df["method"].iloc[0]
    model = df["model"].iloc[0]

    # If gold path supplied, join on doc_id to get gold_topic as true_label
    if gold_path:
        gold = pd.read_csv(gold_path)[["doc_id", "gold_topic"]]
        df = df.merge(gold, on="doc_id", how="inner")
        y_true = df["gold_topic"]
        label_source = "gold_topic"
    else:
        # Use topic_seed; exclude unlabeled rows
        df = df[df["true_label"] != "unlabeled"].copy()
        y_true = df["true_label"]
        label_source = "topic_seed"

    y_pred = df["predicted_label"].fillna("parse_error")

    summary = {
        "method": method,
        "model": model,
        "label_source": label_source,
        "n_predictions": len(df),
        "parse_rate": round((df["predicted_label"].notna()).mean(), 4),
    }

    # Classification metrics — three views
    summary.update(compute_classification_metrics(y_true, y_pred, VALID_CODES, "all_classes"))
    support_10 = [c for c in VALID_CODES if summary.get("per_class_all_classes", {}).get(c, {}).get("support", 0) >= 10]
    summary.update(compute_classification_metrics(y_true, y_pred, support_10, "support_gte10"))
    summary.update(compute_classification_metrics(y_true, y_pred, TRAINABLE_CLASSES, "trainable"))

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=VALID_CODES)
    cm_path = RESULTS_DIR / f"confusion_{method}.csv"
    pd.DataFrame(cm, index=VALID_CODES, columns=VALID_CODES).to_csv(cm_path)
    summary["confusion_matrix_csv"] = str(cm_path)

    # Latency / throughput (nulls for non-LLM methods)
    summary["latency_and_throughput"] = compute_latency_metrics(df)

    # Write JSON
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"eval_summary_{method}.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {out_path}")
    print(f"  macro_f1 (all 9):     {summary.get('macro_f1_all_classes', 'n/a')}")
    print(f"  macro_f1 (support≥10):{summary.get('macro_f1_support_gte10', 'n/a')}")
    print(f"  macro_f1 (trainable): {summary.get('macro_f1_trainable', 'n/a')}")
    lat = summary["latency_and_throughput"]
    if lat["median_latency_s"]:
        print(f"  median latency:       {lat['median_latency_s']}s")
        print(f"  throughput:           {lat['throughput_cards_per_min']} cards/min")
        print(f"  tokens/classification:{lat['tokens_per_classification']}")
        print(f"  tokens/second:        {lat['tokens_per_second']}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate HESA brief classifier predictions"
    )
    parser.add_argument("predictions", type=Path,
                        help="Path to predictions CSV (e.g. results/predictions_baseline_dev.csv)")
    parser.add_argument("--gold", type=Path, default=None,
                        help="Path to gold_test.csv for final evaluation (leave out for dev runs)")
    args = parser.parse_args()

    if not args.predictions.exists():
        print(f"Error: {args.predictions} not found", file=sys.stderr)
        sys.exit(1)

    run_eval(args.predictions, args.gold)


if __name__ == "__main__":
    main()
