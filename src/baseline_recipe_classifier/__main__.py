#!/usr/bin/env python3
"""
Baseline Recipe Time Classifier

Predicts recipe time category based on dish name.
Categories: A (Quick, No-Wait), B (Medium, No-Wait), C (Long, No-Wait),
            D (Short Wait), E (Long Wait)
"""

import argparse
import sys
import re
import yaml
import ollama
import pandas as pd
from pathlib import Path


def load_config(config_path=None):
    """Load configuration from YAML file."""
    if config_path is None:
        # Default to config.yaml in package directory
        import os
        package_dir = os.path.dirname(__file__)
        config_path = os.path.join(package_dir, "config.yaml")

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_recipe_dataset(csv_path):
    """
    Load recipe dataset from CSV file into memory.

    Args:
        csv_path: Path to CSV file

    Returns:
        pandas.DataFrame: Recipe dataset indexed by dish name
    """
    try:
        df = pd.read_csv(csv_path)
        # Set dish name as index for fast lookup
        df.set_index('Name', inplace=True)
        return df
    except FileNotFoundError:
        print(f"Warning: Recipe dataset not found at {csv_path}", file=sys.stderr)
        print("Running in baseline mode without context", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Error loading recipe dataset: {e}", file=sys.stderr)
        print("Running in baseline mode without context", file=sys.stderr)
        return None


def lookup_dish_context(dish_name, dataset):
    """
    Look up dish context from dataset.

    Args:
        dish_name: Name of the dish to look up
        dataset: pandas.DataFrame with recipe data

    Returns:
        dict: Context fields or None if not found
    """
    if dataset is None:
        return None

    try:
        # Exact string match lookup
        recipe = dataset.loc[dish_name]

        # Extract context fields
        context = {}

        # Servings
        if 'Servings' in recipe and pd.notna(recipe['Servings']):
            context['servings'] = recipe['Servings']

        # Ingredient count (split pipe-delimited list)
        if 'Ingredients' in recipe and pd.notna(recipe['Ingredients']):
            ingredients_list = str(recipe['Ingredients']).split('|')
            context['ingredient_count'] = len(ingredients_list)

        # Description
        if 'Description' in recipe and pd.notna(recipe['Description']):
            context['description'] = recipe['Description']

        return context

    except KeyError:
        # Dish not found in dataset
        return None


def format_context(dish_name, context):
    """
    Format context fields into structured string.

    Args:
        dish_name: Name of the dish
        context: Dictionary with context fields

    Returns:
        str: Formatted context string
    """
    if not context:
        return None

    parts = [f"Dish: {dish_name}"]

    if 'servings' in context:
        parts.append(f"Servings: {context['servings']}")

    if 'ingredient_count' in context:
        parts.append(f"Ingredient count: {context['ingredient_count']}")

    if 'description' in context:
        parts.append(f"Description: {context['description']}")

    return ", ".join(parts)


def build_prompt(dish_name, categories, context=None):
    """
    Build zero-shot classification prompt.

    Args:
        dish_name: Name of the dish
        categories: Dictionary of category definitions
        context: Optional formatted context string

    Returns:
        str: Complete prompt for LLM
    """

    # Build category descriptions
    category_text = "\n".join([
        f"{code}: {info['name']} - {info['description']}"
        for code, info in categories.items()
    ])

    # Use context if provided, otherwise just dish name
    input_text = context if context else f"Dish: {dish_name}"

    prompt = f"""You are a recipe time classifier. Given a dish name and optional context, predict which time category it belongs to.

Categories:
{category_text}

Instructions:
- Analyze the dish information provided
- Consider typical preparation requirements
- Respond with ONLY the category letter (A, B, C, D, or E)
- Do not include explanation

Input: {input_text}

Category:"""

    return prompt


def predict_category(dish_name, config, dataset=None, use_context=True):
    """
    Predict recipe time category using Ollama.

    Args:
        dish_name: Name of the dish to classify
        config: Configuration dictionary
        dataset: Optional pandas DataFrame with recipe data
        use_context: Whether to use context if available (default: True)

    Returns:
        str: Predicted category code (A-E) or None if parsing fails
    """

    # Try to get context if requested and dataset available
    context_str = None
    if use_context and dataset is not None:
        context = lookup_dish_context(dish_name, dataset)
        if context:
            context_str = format_context(dish_name, context)

    # Build prompt with or without context
    prompt = build_prompt(dish_name, config['categories'], context_str)

    # Call Ollama
    try:
        response = ollama.chat(
            model=config['model']['name'],
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            options={
                'temperature': config['model']['temperature']
            }
        )

        # Extract response text
        response_text = response['message']['content'].strip()

        # Parse category (look for A, B, C, D, or E)
        match = re.search(r'\b([A-E])\b', response_text, re.IGNORECASE)

        if match:
            return match.group(1).upper()
        else:
            print(f"Warning: Could not parse category from response: {response_text}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Error calling Ollama: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Classify recipe time category from dish name"
    )
    parser.add_argument(
        "dish_name",
        type=str,
        help="Name of the dish to classify"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file (default: config.yaml in package directory)"
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Disable context retrieval (baseline mode)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to recipe dataset CSV (overrides config)"
    )

    args = parser.parse_args()

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config file: {e}", file=sys.stderr)
        sys.exit(1)

    # Load dataset if context is enabled
    dataset = None
    if not args.no_context:
        # Determine dataset path
        if args.dataset:
            dataset_path = args.dataset
        elif 'dataset' in config and 'path' in config['dataset']:
            # Resolve path relative to project root (2 levels up from package dir)
            import os
            package_dir = os.path.dirname(__file__)
            project_root = os.path.dirname(os.path.dirname(package_dir))
            dataset_path = os.path.join(project_root, config['dataset']['path'])
        else:
            print("Warning: No dataset path configured", file=sys.stderr)
            dataset_path = None

        if dataset_path:
            dataset = load_recipe_dataset(dataset_path)
            if dataset is not None:
                print(f"Loaded dataset with {len(dataset)} recipes")

    # Predict
    print(f"Classifying: {args.dish_name}")
    print(f"Using model: {config['model']['name']}")
    mode = "baseline" if args.no_context or dataset is None else "context-enhanced"
    print(f"Mode: {mode}")
    print()

    category = predict_category(
        args.dish_name,
        config,
        dataset=dataset,
        use_context=not args.no_context
    )

    if category:
        category_info = config['categories'][category]
        print(f"Predicted Category: {category}")
        print(f"Category Name: {category_info['name']}")
        print(f"Description: {category_info['description']}")
    else:
        print("Failed to predict category")
        sys.exit(1)


if __name__ == '__main__':
    main()
