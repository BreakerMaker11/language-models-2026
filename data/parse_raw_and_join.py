"""
Parse raw recipe data (corbt/all-recipes parquet files) and join Directions
into the labeled CSV (All_Recipe_Web_Scraping_Dataset_Labeled.csv).

Each row in the raw parquet has a single 'input' column with the format:
    <Recipe Name>

    Ingredients:
    - ingredient 1
    - ...

    Directions:
    - step 1
    - ...

Output: All_Recipe_Web_Scraping_Dataset_With_Directions.csv
"""

import glob
import os
import re

import pandas as pd

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "raw_data")
HF_BLOB_DIR = os.path.expanduser(
    "~/.cache/huggingface/hub/datasets--corbt--all-recipes/blobs"
)
CSV_PATH = os.path.join(os.path.dirname(__file__), "All_Recipe_Web_Scraping_Dataset_Labeled.csv")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "All_Recipe_Web_Scraping_Dataset_With_Directions.csv")


def load_raw_data() -> pd.DataFrame:
    """Load all parquet shards; fall back to HF cache if symlinks are broken."""
    files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, "*.parquet")))
    if not files:
        raise FileNotFoundError(f"No parquet files found in {RAW_DATA_DIR}")

    try:
        dfs = [pd.read_parquet(f) for f in files]
        print(f"Loaded {len(files)} parquet shard(s) from {RAW_DATA_DIR}")
    except (FileNotFoundError, OSError):
        # Symlinks point to a relative blob path that doesn't exist locally;
        # fall back to the HuggingFace cache.
        print(f"Symlinks broken — falling back to HF cache at {HF_BLOB_DIR}")
        blobs = [
            os.path.join(HF_BLOB_DIR, f)
            for f in os.listdir(HF_BLOB_DIR)
            if len(f) == 64  # sha256 hex blobs only (not JSON metadata files)
        ]
        if not blobs:
            raise FileNotFoundError(f"No blob files found in {HF_BLOB_DIR}")
        dfs = [pd.read_parquet(b) for b in blobs]
        print(f"Loaded {len(blobs)} blob(s) from HF cache")

    return pd.concat(dfs, ignore_index=True)


def parse_input(text: str) -> pd.Series:
    """Extract recipe name, ingredients text, and directions from a raw input string."""
    name_match = re.match(r"^(.+?)\n", text)
    name = name_match.group(1).strip() if name_match else ""

    directions_match = re.search(r"Directions:\n(.*?)$", text, re.DOTALL)
    directions = directions_match.group(1).strip() if directions_match else ""

    return pd.Series({"raw_name": name, "directions": directions})


def main():
    # --- Load raw data ---
    raw_df = load_raw_data()
    print(f"Total raw rows: {len(raw_df):,}")

    # --- Parse each input string ---
    print("Parsing input strings...")
    parsed = raw_df["input"].apply(parse_input)
    raw_df = pd.concat([raw_df, parsed], axis=1)

    # Normalize name for joining
    raw_df["_key"] = raw_df["raw_name"].str.lower().str.strip()

    # Deduplicate: keep first occurrence per normalized key
    raw_df = raw_df.drop_duplicates(subset="_key")
    print(f"Unique recipe names in raw data: {len(raw_df):,}")

    # --- Load labeled CSV ---
    csv_df = pd.read_csv(CSV_PATH)
    print(f"Labeled CSV rows: {len(csv_df):,}")

    # --- Join on normalized recipe name ---
    csv_df["_key"] = csv_df["Name"].str.lower().str.strip()

    merged = csv_df.merge(
        raw_df[["_key", "directions"]],
        on="_key",
        how="left",
    ).drop(columns="_key")

    matched = merged["directions"].notna().sum()
    print(f"Matched {matched:,} / {len(merged):,} rows with directions")

    # --- Save output ---
    merged.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved to {OUTPUT_PATH}")

    # Quick preview
    print("\nSample output:")
    print(merged[["Name", "directions"]].head(3).to_string(max_colwidth=80))


if __name__ == "__main__":
    main()
