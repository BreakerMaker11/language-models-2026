"""
Pure scorer: load predictions CSV → join gold → compute metrics → write artifacts.

Usage:
    uv run python -m eval.harness --predictions results/X.csv --method NAME
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

LABELS = [
    "public_health",
    "pharmacare",
    "womens_health",
    "workforce",
    "childrens_health",
    "mental_health",
    "cancer",
    "indigenous_health",
    "other_none",
]

GOLD_PATH = Path("data/health/gold_test.csv")
TRAIN_PATH = Path("data/health/train.csv")
RESULTS_DIR = Path("results")


def _trainable_classes() -> list[str]:
    """Classes that appear as non-unlabeled topic_seed in train.csv."""
    train = pd.read_csv(TRAIN_PATH)
    seeds = train.loc[train["topic_seed"] != "unlabeled", "topic_seed"].unique()
    return [c for c in LABELS if c in seeds]


def _load_and_align(predictions_path: str) -> pd.DataFrame:
    pred = pd.read_csv(predictions_path)

    # Dedupe: for each doc_id keep a non-failed row if one exists
    if "parse_method" in pred.columns:
        pred = pred.sort_values(
            "parse_method",
            key=lambda s: s.map(lambda v: 0 if v != "failed" else 1),
        )
    pred = pred.drop_duplicates(subset="doc_id", keep="first")

    gold = pd.read_csv(GOLD_PATH)[["doc_id", "gold_topic"]]
    assert len(gold) == 217, f"Expected 217 gold rows, got {len(gold)}"

    merged = gold.merge(pred, on="doc_id", how="left")

    # Every gold doc_id must be in the output
    assert len(merged) == 217, f"Merge produced {len(merged)} rows"

    # Map missing / invalid / failed to "PARSE_FAIL"
    valid = set(LABELS)
    if "predicted_label" not in merged.columns:
        merged["predicted_label"] = None

    def _clean(v):
        if pd.isna(v) or str(v).strip() not in valid:
            return "PARSE_FAIL"
        return str(v).strip()

    merged["predicted_label"] = merged["predicted_label"].apply(_clean)
    return merged


def _efficiency(df: pd.DataFrame) -> dict:
    out: dict = {
        "median_latency_s": None,
        "median_prompt_tokens": None,
        "median_output_tokens": None,
        "tokens_per_classification": None,
        "cards_per_min": None,
    }
    if "total_duration_ms" in df.columns and df["total_duration_ms"].notna().any():
        lat_s = df["total_duration_ms"] / 1000.0
        out["median_latency_s"] = round(float(lat_s.median()), 3)
        out["cards_per_min"] = round(60.0 / float(lat_s.median()), 2)
    if "prompt_tokens" in df.columns and df["prompt_tokens"].notna().any():
        out["median_prompt_tokens"] = int(df["prompt_tokens"].median())
    if "output_tokens" in df.columns and df["output_tokens"].notna().any():
        out["median_output_tokens"] = int(df["output_tokens"].median())
    if out["median_prompt_tokens"] and out["median_output_tokens"]:
        out["tokens_per_classification"] = (
            out["median_prompt_tokens"] + out["median_output_tokens"]
        )
    return out


def _parse_method_dist(df: pd.DataFrame) -> dict:
    if "parse_method" in df.columns:
        return df["parse_method"].value_counts().to_dict()
    return {}


def run(predictions_path: str, method: str) -> dict:
    RESULTS_DIR.mkdir(exist_ok=True)

    df = _load_and_align(predictions_path)

    n_missing = int(df["predicted_label"].isna().sum())  # should be 0 after _clean
    n_parse_fail = int((df["predicted_label"] == "PARSE_FAIL").sum())

    y_true = df["gold_topic"].tolist()
    y_pred = df["predicted_label"].tolist()

    # All sklearn calls use LABELS explicitly; PARSE_FAIL may appear in y_pred
    # but won't appear in LABELS so it scores as 0 recall on every real class.
    eval_labels = LABELS  # keep denominator fixed

    report = classification_report(
        y_true,
        y_pred,
        labels=eval_labels,
        target_names=eval_labels,
        output_dict=True,
        zero_division=0,
    )
    accuracy = accuracy_score(y_true, y_pred)

    # support-≥10 classes (from gold distribution)
    support_10 = [c for c in LABELS if report[c]["support"] >= 10]
    trainable = _trainable_classes()

    macro_f1_all = f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    macro_f1_support10 = (
        f1_score(y_true, y_pred, labels=support_10, average="macro", zero_division=0)
        if support_10 else 0.0
    )
    macro_f1_trainable = (
        f1_score(y_true, y_pred, labels=trainable, average="macro", zero_division=0)
        if trainable else 0.0
    )

    # Confusion matrix (rows=true, cols=predicted)
    # Use full label list for axes; PARSE_FAIL may appear in y_pred as extra col
    cm_labels = LABELS + (["PARSE_FAIL"] if n_parse_fail > 0 else [])
    cm = confusion_matrix(y_true, y_pred, labels=cm_labels)
    cm_df = pd.DataFrame(cm, index=cm_labels, columns=cm_labels)
    cm_csv = RESULTS_DIR / f"confusion_{method}.csv"
    cm_df.to_csv(cm_csv)

    fig, ax = plt.subplots(figsize=(max(10, len(cm_labels)), max(8, len(cm_labels) - 1)))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.set_xticks(range(len(cm_labels)))
    ax.set_yticks(range(len(cm_labels)))
    ax.set_xticklabels(cm_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(cm_labels, fontsize=8)
    for i in range(len(cm_labels)):
        for j in range(len(cm_labels)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=7)
    ax.set_ylabel("True label")
    ax.set_xlabel("Predicted label")
    ax.set_title(f"Confusion matrix — {method}")
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    png_path = RESULTS_DIR / f"confusion_{method}.png"
    plt.savefig(png_path, dpi=150)
    plt.close()

    # Infer model name
    model_name = None
    if "model" in df.columns and df["model"].notna().any():
        model_name = df["model"].dropna().iloc[0]

    summary = {
        "method": method,
        "model": model_name,
        "n": 217,
        "accuracy": round(accuracy, 4),
        "macro_f1_all": round(macro_f1_all, 4),
        "macro_f1_support10": round(macro_f1_support10, 4),
        "macro_f1_trainable": round(macro_f1_trainable, 4),
        "per_class": {
            c: {
                "p": round(report[c]["precision"], 4),
                "r": round(report[c]["recall"], 4),
                "f1": round(report[c]["f1-score"], 4),
                "support": int(report[c]["support"]),
            }
            for c in LABELS
        },
        "efficiency": _efficiency(df),
        "failures": {
            "n_parse_fail": n_parse_fail,
            "n_missing": n_missing,
            "parse_method_dist": _parse_method_dist(df),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "predictions_file": str(predictions_path),
    }

    json_path = RESULTS_DIR / f"eval_summary_{method}.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    _print_table(summary, support_10, trainable)
    return summary


def _print_table(s: dict, support_10: list[str], trainable: list[str]) -> None:
    w = 72
    print("\n" + "=" * w)
    print(f"  {s['method']}  |  model: {s['model'] or '—'}  |  n={s['n']}")
    print("=" * w)
    print(f"  Accuracy          {s['accuracy']:.4f}")
    print(f"  Macro-F1 (all 9)  {s['macro_f1_all']:.4f}")
    print(f"  Macro-F1 (sup≥10) {s['macro_f1_support10']:.4f}  classes: {support_10}")
    print(f"  Macro-F1 (train.) {s['macro_f1_trainable']:.4f}  classes: {trainable}")
    print("-" * w)
    hdr = f"  {'Class':<22} {'P':>6} {'R':>6} {'F1':>6} {'N':>5}"
    print(hdr)
    print("-" * w)
    for lbl, m in s["per_class"].items():
        print(f"  {lbl:<22} {m['p']:>6.3f} {m['r']:>6.3f} {m['f1']:>6.3f} {m['support']:>5}")
    print("-" * w)
    fails = s["failures"]
    print(f"  parse_fail={fails['n_parse_fail']}  missing={fails['n_missing']}  "
          f"parse_dist={fails['parse_method_dist']}")
    eff = s["efficiency"]
    if eff["median_latency_s"]:
        print(f"  latency_median={eff['median_latency_s']}s  "
              f"cards/min={eff['cards_per_min']}  "
              f"tokens/call={eff['tokens_per_classification']}")
    print("=" * w + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--method", required=True)
    args = parser.parse_args()
    run(args.predictions, args.method)


if __name__ == "__main__":
    main()
