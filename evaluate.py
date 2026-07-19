import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, f1_score

# Define the absolute class-space universe as mandated by the charter
ALL_CLASSES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health", "other_none"
]

# Define sub-cohorts for macro-F1 tracking
TRAINABLE_CLASSES = [c for c in ALL_CLASSES if c not in ["mental_health", "indigenous_health", "cancer"]]

def run_evaluation(predictions_path, gold_path, method_name, output_dir="results"):
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    gold_df = pd.read_csv(gold_path)
    pred_df = pd.read_csv(predictions_path)
    
    # Align rows on index or unique identifier if applicable, 
    # assuming they follow identical order or have a matching key.
    # Adjust merge strategy if your CSVs use a specific ID column (e.g., card_text or doc_id)
    y_true = gold_df["gold_topic"].tolist()
    y_pred = pred_df["predicted_topic"].tolist()
    
    # 1. Generate standard per-class metrics forcing full class space
    report = classification_report(
        y_true, y_pred, 
        labels=ALL_CLASSES, 
        target_names=ALL_CLASSES, 
        output_dict=True, 
        zero_division=0
    )
    
    # 2. Calculate the 3 required macro-F1 variations
    # Macro-F1: All 9 classes
    macro_f1_all = f1_score(y_true, y_pred, labels=ALL_CLASSES, average="macro", zero_division=0)
    
    # Macro-F1: Classes with support >= 10 in gold_test
    classes_gt_10 = [c for c in ALL_CLASSES if report[c]["support"] >= 10]
    macro_f1_gt_10 = f1_score(y_true, y_pred, labels=classes_gt_10, average="macro", zero_division=0) if classes_gt_10 else 0.0
    
    # Macro-F1: Trainable classes only (excluding the 3 zero-train classes)
    macro_f1_trainable = f1_score(y_true, y_pred, labels=TRAINABLE_CLASSES, average="macro", zero_division=0)
    
    # Build uniform JSON structure
    eval_summary = {
        "method": method_name,
        "accuracy": report["accuracy"] if "accuracy" in report else None,
        "macro_f1": {
            "all_classes": macro_f1_all,
            "support_gte_10": macro_f1_gt_10,
            "trainable_classes_only": macro_f1_trainable
        },
        "per_class": {c: report[c] for c in ALL_CLASSES}
    }
    
    # Save json summary
    json_out = os.path.join(output_dir, f"eval_summary_{method_name}.json")
    with open(json_out, "w") as f:
        json.dump(eval_summary, f, indent=4)
        
    # 3. Generate and save Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=ALL_CLASSES)
    cm_df = pd.DataFrame(cm, index=ALL_CLASSES, columns=ALL_CLASSES)
    
    # Save confusion matrix CSV
    cm_df.to_csv(os.path.join(output_dir, f"confusion_matrix_{method_name}.csv"))
    
    # Plot and save confusion matrix PNG
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.title(f"Confusion Matrix - {method_name}")
    plt.ylabel("Actual Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"confusion_matrix_{method_name}.png"), dpi=300)
    plt.close()
    
    print(f"Evaluation complete. Artifacts written to {output_dir}/ for method: {method_name}")
    print(f"Macro-F1 (All): {macro_f1_all:.4f} | Macro-F1 (Trainable): {macro_f1_trainable:.4f}")

if __name__ == "__main__":
    # Example execution for your zero-shot run
    run_evaluation(
        predictions_path="predictions_zeroshot_gemma4-12b_gold.csv",
        gold_path="data/health/gold_test.csv",
        method_name="zeroshot_gemma4-12b"
    )