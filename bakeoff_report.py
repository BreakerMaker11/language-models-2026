#!/usr/bin/env python3
"""
Post-bakeoff report: per-model stats + head-to-head disagreements.
Also writes results/disagreement_cards.txt for manual codebook review.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

RESULTS = Path("results")
VALID_CODES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health", "other_none",
]


def per_model_stats(df: pd.DataFrame, model: str) -> None:
    g = df[df["model"] == model].copy()
    if g.empty:
        print(f"  (no rows for {model})")
        return
    total = len(g)
    parsed = g["predicted_label"].notna().sum()
    labeled = g[g["true_label"] != "unlabeled"]
    agreed = (labeled["predicted_label"] == labeled["true_label"]).sum()
    weak_agr = agreed / len(labeled) * 100 if len(labeled) else 0
    med_lat = g["total_duration_ms"].median() / 1000 if g["total_duration_ms"].notna().any() else None
    med_out = g["output_tokens"].median() if g["output_tokens"].notna().any() else None

    print(f"  Parse rate       : {parsed}/{total} ({parsed/total*100:.0f}%)")
    print(f"  Weak-agreement   : {agreed}/{len(labeled)} labeled ({weak_agr:.0f}%)")
    print(f"  Median latency   : {med_lat:.1f}s" if med_lat is not None else "  Median latency   : n/a")
    print(f"  Median out tokens: {int(med_out)}" if med_out is not None else "  Median out tokens: n/a")


def main():
    csv = RESULTS / "predictions_baseline_dev.csv"
    dev_csv = Path("data/health/dev.csv")

    if not csv.exists():
        print(f"Error: {csv} not found", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv)
    dev = pd.read_csv(dev_csv)[["doc_id", "card_text"]]

    models = sorted(df["model"].unique())
    for model in models:
        print(f"\n=== {model} ===")
        per_model_stats(df, model)

    # Head-to-head: need exactly the two bakeoff models
    if len(models) < 2:
        print("\nNeed both models in CSV to compute disagreements.")
        return

    m1, m2 = models[0], models[1]
    p1 = df[df["model"] == m1][["doc_id", "true_label", "predicted_label"]].rename(columns={"predicted_label": m1})
    p2 = df[df["model"] == m2][["doc_id", "true_label", "predicted_label"]].rename(columns={"predicted_label": m2})
    merged = p1.merge(p2, on=["doc_id", "true_label"])

    disagree = merged[merged[m1] != merged[m2]].copy()
    disagree = disagree.merge(dev, on="doc_id", how="left")

    print(f"\n=== Head-to-head disagreements: {len(disagree)}/{len(merged)} cards ===")
    for _, r in disagree.iterrows():
        print(f"  {r['doc_id']}")
        print(f"    true={r['true_label']}  {m1}={r[m1] or 'PARSE_ERR'}  {m2}={r[m2] or 'PARSE_ERR'}")

    # Export card texts for manual review
    out = RESULTS / "disagreement_cards.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"Disagreement cards for manual codebook review\n")
        f.write(f"Models: {m1}  vs  {m2}\n")
        f.write("=" * 72 + "\n\n")
        for _, r in disagree.iterrows():
            f.write(f"doc_id     : {r['doc_id']}\n")
            f.write(f"true_label : {r['true_label']}\n")
            f.write(f"{m1:<12}: {r[m1] or 'PARSE_ERR'}\n")
            f.write(f"{m2:<12}: {r[m2] or 'PARSE_ERR'}\n")
            f.write(f"\ncard_text:\n{r.get('card_text', '(not found)')}\n")
            f.write("\n" + "-" * 72 + "\n\n")
    print(f"\nCard texts written → {out}")


if __name__ == "__main__":
    main()
