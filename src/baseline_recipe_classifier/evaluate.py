#!/usr/bin/env python3
"""
Evaluation script for recipe classifier.
Runs ablation study comparing baseline vs. context-enhanced predictions.
"""

import sys
import pandas as pd
from pathlib import Path
from baseline_recipe_classifier.__main__ import (
    load_config,
    load_recipe_dataset,
    predict_category
)


def evaluate_classifier(test_dishes, config, dataset=None, use_context=True):
    """
    Evaluate classifier on test dishes.

    Args:
        test_dishes: List of (dish_name, ground_truth_category) tuples
        config: Configuration dictionary
        dataset: Optional recipe dataset
        use_context: Whether to use context

    Returns:
        tuple: (accuracy, correct_count, total_count, predictions)
    """
    predictions = []
    correct = 0
    total = len(test_dishes)

    for dish_name, ground_truth in test_dishes:
        predicted = predict_category(
            dish_name,
            config,
            dataset=dataset,
            use_context=use_context
        )

        is_correct = predicted == ground_truth
        if is_correct:
            correct += 1

        predictions.append({
            'dish': dish_name,
            'ground_truth': ground_truth,
            'predicted': predicted,
            'correct': is_correct
        })

    accuracy = (correct / total * 100) if total > 0 else 0
    return accuracy, correct, total, predictions


def print_results(mode, accuracy, correct, total, predictions, verbose=False):
    """Print evaluation results."""
    print(f"\n{'='*60}")
    print(f"{mode.upper()} MODE")
    print(f"{'='*60}")
    print(f"Accuracy: {accuracy:.1f}% ({correct}/{total})")

    if verbose:
        print(f"\nDetailed Results:")
        for pred in predictions:
            status = "✓" if pred['correct'] else "✗"
            print(f"  {status} {pred['dish'][:40]:40} | GT: {pred['ground_truth']} | Pred: {pred['predicted']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate recipe classifier with ablation study"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to labeled dataset CSV"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=10,
        help="Number of test samples (default: 10)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed predictions"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)"
    )

    args = parser.parse_args()

    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine dataset path
    if args.dataset:
        dataset_path = args.dataset
    elif 'dataset' in config and 'path' in config['dataset']:
        import os
        package_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(package_dir))
        dataset_path = os.path.join(project_root, config['dataset']['path'])
    else:
        print("Error: No dataset path provided", file=sys.stderr)
        sys.exit(1)

    # Load dataset
    print(f"Loading dataset from: {dataset_path}")
    dataset = load_recipe_dataset(dataset_path)

    if dataset is None:
        print("Error: Failed to load dataset", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(dataset)} recipes")

    # Check for ground truth labels
    if 'Category Code' not in dataset.columns:
        print("Error: Dataset missing 'Category Code' column", file=sys.stderr)
        sys.exit(1)

    # Sample test dishes (filter out any with missing labels)
    labeled_dataset = dataset[dataset['Category Code'].notna()].copy()
    print(f"Found {len(labeled_dataset)} labeled recipes")

    if len(labeled_dataset) < args.num_samples:
        print(f"Warning: Only {len(labeled_dataset)} labeled recipes available", file=sys.stderr)
        num_samples = len(labeled_dataset)
    else:
        num_samples = args.num_samples

    # Random sample
    test_sample = labeled_dataset.sample(n=num_samples, random_state=args.seed)

    # Create test dishes list
    test_dishes = [
        (dish_name, row['Category Code'])
        for dish_name, row in test_sample.iterrows()
    ]

    print(f"\nRunning ablation study with {num_samples} test samples...")
    print(f"Using model: {config['model']['name']}")

    # Run baseline evaluation (no context)
    print("\n[1/2] Running baseline (no context)...")
    baseline_accuracy, baseline_correct, baseline_total, baseline_predictions = evaluate_classifier(
        test_dishes,
        config,
        dataset=None,
        use_context=False
    )

    # Run context-enhanced evaluation
    print("\n[2/2] Running context-enhanced...")
    context_accuracy, context_correct, context_total, context_predictions = evaluate_classifier(
        test_dishes,
        config,
        dataset=dataset,
        use_context=True
    )

    # Print results
    print_results("Baseline", baseline_accuracy, baseline_correct, baseline_total, baseline_predictions, args.verbose)
    print_results("Context-Enhanced", context_accuracy, context_correct, context_total, context_predictions, args.verbose)

    # Print comparison
    improvement = context_accuracy - baseline_accuracy
    print(f"\n{'='*60}")
    print(f"COMPARISON")
    print(f"{'='*60}")
    print(f"Baseline:         {baseline_accuracy:.1f}%")
    print(f"Context-Enhanced: {context_accuracy:.1f}%")
    print(f"Improvement:      {improvement:+.1f} percentage points")

    if improvement > 0:
        print(f"\n✓ Context improved accuracy!")
    elif improvement < 0:
        print(f"\n✗ Context decreased accuracy")
    else:
        print(f"\n− No change in accuracy")

    print(f"\nTest samples: {num_samples}")
    print(f"Random seed: {args.seed}")


if __name__ == '__main__':
    main()
