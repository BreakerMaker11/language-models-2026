"""
Precompute gap analysis for the 8 CMA sections.

For each section in demo/cma_sections.json, runs ask() three times —
once per source_type filter (hesa_brief, hesa_report, gov_response) — and
writes results/gap_analysis.json.

The `status` field is set to "TODO" for all layers. Fill it by hand after
reading the answers: echoed / endorsed / committed / unaddressed.

Usage:
    export OLLAMA_HOST=http://100.85.195.54:11434
    uv run --no-sync python scripts/precompute_gap.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.ask import ask

DEMO_PATH   = PROJECT_ROOT / "demo" / "cma_sections.json"
OUTPUT_PATH = PROJECT_ROOT / "results" / "gap_analysis.json"

SOURCE_TYPES = ["hesa_brief", "hesa_report", "gov_response"]
K = 3


def main() -> None:
    with open(DEMO_PATH) as f:
        cma = json.load(f)

    sections_in = cma["sections"]
    print(f"Processing {len(sections_in)} CMA sections × {len(SOURCE_TYPES)} filters …\n")

    output_sections = []

    for sec in sections_in:
        print(f"── {sec['title']} ──")
        layers = {}

        for src_type in SOURCE_TYPES:
            print(f"   {src_type} … ", end="", flush=True)
            t0 = time.perf_counter()
            try:
                answer, passages = ask(sec["ask_text"], source_type_filter=src_type, k=K)
                elapsed = time.perf_counter() - t0
                print(f"OK ({elapsed:.1f}s)")
            except Exception as e:
                print(f"FAILED: {e}")
                answer = f"[Error: {e}]"
                passages = []

            # Serialize passages (metadata may contain non-JSON-serialisable types)
            serialised_passages = []
            for p in passages:
                serialised_passages.append({
                    "doc_id":   p["doc_id"],
                    "text":     p["text"],
                    "distance": float(p["distance"]),
                    "metadata": {k: (v if v is not None else "") for k, v in p["metadata"].items()},
                })

            layers[src_type] = {
                "answer":   answer,
                "passages": serialised_passages,
                "status":   "TODO",  # fill by hand: echoed / endorsed / committed / unaddressed
            }

        output_sections.append({
            "section_id": sec["section_id"],
            "title":      sec["title"],
            "ask_text":   sec["ask_text"],
            "layers":     layers,
        })
        print()

    result = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "source_filters": SOURCE_TYPES,
        "k":              K,
        "note":           (
            "status field is TODO — fill by hand after reading answers. "
            "Valid values: echoed / endorsed / committed / unaddressed."
        ),
        "sections": output_sections,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Written → {OUTPUT_PATH}")
    print("Next: open the file and fill in each 'status' field by hand.")


if __name__ == "__main__":
    main()
