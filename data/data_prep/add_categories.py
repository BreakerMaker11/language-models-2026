#!/usr/bin/env python3
"""
Add time-based classification labels to All Recipes dataset.

Categories:
  A - Quick, No-Wait:   Total time ≤ 30 min, no wait
  B - Medium, No-Wait:  30 < total ≤ 60 min, no wait
  C - Long, No-Wait:    Total time > 60 min, no wait
  D - Short Wait:       Wait time 1-30 min
  E - Long Wait:        Wait time > 30 min
"""

import pandas as pd
import re
import sys

def parse_time_to_minutes(time_str):
    """Convert time string like '2 hrs 30 mins' to total minutes."""
    if pd.isna(time_str) or time_str == 'None':
        return None

    time_str = str(time_str).strip()
    total_mins = 0

    # Match hours
    hrs_match = re.search(r'(\d+)\s*hrs?', time_str, re.IGNORECASE)
    if hrs_match:
        total_mins += int(hrs_match.group(1)) * 60

    # Match minutes
    mins_match = re.search(r'(\d+)\s*mins?', time_str, re.IGNORECASE)
    if mins_match:
        total_mins += int(mins_match.group(1))

    return total_mins if total_mins > 0 else None

def categorize_recipe(prep_mins, cook_mins, total_mins):
    """
    Categorize recipe based on time requirements.

    Returns:
        tuple: (category_code, category_name, category_description)
    """
    if pd.isna(prep_mins) or pd.isna(cook_mins) or pd.isna(total_mins):
        return None, None, None

    wait_mins = total_mins - (prep_mins + cook_mins)

    if wait_mins <= 0:
        if total_mins <= 30:
            return 'A', 'Quick, No-Wait', 'Total time ≤ 30 min, no wait'
        elif total_mins <= 60:
            return 'B', 'Medium, No-Wait', '30 < total ≤ 60 min, no wait'
        else:
            return 'C', 'Long, No-Wait', 'Total time > 60 min, no wait'
    else:
        if wait_mins <= 30:
            return 'D', 'Short Wait', 'Wait time 1-30 min'
        else:
            return 'E', 'Long Wait', 'Wait time > 30 min'

def main():
    input_file = 'All_Recipe_Web_Scraping_Dataset.csv'
    output_file = 'All_Recipe_Web_Scraping_Dataset_Labeled.csv'

    print("="*70)
    print("ADDING CATEGORIES TO ALL RECIPES DATASET")
    print("="*70)

    # Load CSV
    print(f"\nLoading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} recipes")

    # Parse times
    print("\nParsing time fields...")
    df['prep_mins'] = df['Prep Time'].apply(parse_time_to_minutes)
    df['cook_mins'] = df['Cook Time'].apply(parse_time_to_minutes)
    df['total_mins'] = df['Total Time'].apply(parse_time_to_minutes)

    # Calculate wait time
    df['wait_mins'] = df['total_mins'] - (df['prep_mins'].fillna(0) + df['cook_mins'].fillna(0))

    # Categorize
    print("Categorizing recipes...")
    categories = df.apply(
        lambda row: categorize_recipe(row['prep_mins'], row['cook_mins'], row['total_mins']),
        axis=1
    )

    df['Category Code'] = categories.apply(lambda x: x[0] if x[0] else None)
    df['Category Name'] = categories.apply(lambda x: x[1] if x[1] else None)
    df['Category Description'] = categories.apply(lambda x: x[2] if x[2] else None)

    # Count categories
    print("\n" + "="*70)
    print("CATEGORY DISTRIBUTION")
    print("="*70)

    category_counts = df['Category Code'].value_counts().sort_index()
    total_valid = df['Category Code'].notna().sum()
    total_missing = df['Category Code'].isna().sum()

    category_info = {
        'A': 'Quick, No-Wait',
        'B': 'Medium, No-Wait',
        'C': 'Long, No-Wait',
        'D': 'Short Wait',
        'E': 'Long Wait'
    }

    for code in ['A', 'B', 'C', 'D', 'E']:
        count = category_counts.get(code, 0)
        pct = (count / total_valid) * 100 if total_valid > 0 else 0
        print(f"{code} - {category_info[code]:20} {count:6} recipes ({pct:5.1f}%)")

    print(f"\nMissing category (incomplete time data): {total_missing} recipes")
    print(f"Total valid: {total_valid}")
    print(f"Total recipes: {len(df)}")

    # Save
    print(f"\nSaving to {output_file}...")
    df.to_csv(output_file, index=False)
    print("Done!")

    # Show examples
    print("\n" + "="*70)
    print("SAMPLE RECIPES FROM EACH CATEGORY")
    print("="*70)

    for code in ['A', 'B', 'C', 'D', 'E']:
        print(f"\n{code} - {category_info[code]}:")
        examples = df[df['Category Code'] == code].head(3)
        for idx, row in examples.iterrows():
            print(f"  • {row['Name']}")
            print(f"    Prep: {row['prep_mins']:.0f}min | Cook: {row['cook_mins']:.0f}min | Total: {row['total_mins']:.0f}min | Wait: {row['wait_mins']:.0f}min")

if __name__ == '__main__':
    main()
