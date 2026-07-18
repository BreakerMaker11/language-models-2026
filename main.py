#!/usr/bin/env python3
"""
HESA Health-Policy Brief Classifier — Week 1 baseline (zero-shot, definitions only).

Modes:
  --all-dev        classify every row of dev.csv in doc_id order
  --text "..."     classify a single card text supplied on the command line
  --doc-id ID      classify a single card looked up by doc_id in dev.csv
"""

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_RETRY_ATTEMPTS = 4
_RETRY_BACKOFF_S = 30
_WARMUP_ATTEMPTS = 48   # 48 × 5s = 4 min ceiling; poll frequently to catch the load window
_WARMUP_BACKOFF_S = 5

import httpx
import ollama
import pandas as pd
import yaml

# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "src" / "baseline_recipe_classifier" / "config.yaml"
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_CSV = RESULTS_DIR / "predictions_baseline_dev.csv"
OUTPUT_COLS = [
    "doc_id", "true_label", "predicted_label", "raw_output",
    "parse_method", "parse_candidates",
    "method", "model", "timestamp",
    "prompt_tokens", "output_tokens", "total_duration_ms", "load_duration_ms",
]
FAILED_CSV = RESULTS_DIR / "failed_cards.csv"

RANDOM_SEED = 42
METHOD = "baseline_zeroshot"

# ── Config loading ────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def health_model(cfg, model_override: str | None = None):
    """Return (model_name, temperature, num_ctx, ollama_options) from health.models.*"""
    name = model_override or cfg["health"]["default_model"]   # health.default_model
    models = cfg["health"]["models"]                          # health.models.*
    if name not in models:
        raise ValueError(f"Model {name!r} not in config health.models. "
                         f"Known: {list(models)}")
    m = models[name]
    return name, m["temperature"], m["num_ctx"], dict(m.get("ollama_options", {}))


def health_categories(cfg):
    """Return ordered dict {code: description} from health.categories."""
    return {
        code: info["description"].strip()
        for code, info in cfg["health"]["categories"].items()   # health.categories.*
    }


def health_dev_path(cfg):
    """Resolve data/health/dev.csv from health.dataset.dev key."""
    rel = cfg["health"]["dataset"]["dev"]               # health.dataset.dev
    return PROJECT_ROOT / rel


def health_train_path(cfg):
    rel = cfg["health"]["dataset"]["train"]             # health.dataset.train
    return PROJECT_ROOT / rel


# gold_test path intentionally not used at runtime — frozen evaluation only
# cfg["health"]["dataset"]["gold_test"]                 # health.dataset.gold_test

VALID_CODES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health",
    "other_none",
]

# ── Prompt builder ────────────────────────────────────────────────────────────

SYSTEM = (
    "You are a policy document classifier. "
    "Assign exactly one topic code from the list below. "
    "Respond with exactly one category code and nothing else."
)

RULE2 = (
    "Precedence rule: womens_health beats cancer for breast/cervical cancer; "
    "indigenous_health beats mental_health; "
    "childrens_health beats cancer for pediatric oncology."
)


def build_prompt(card_text: str, categories: dict) -> str:
    defs = "\n".join(f"{code}: {desc}" for code, desc in categories.items())
    codes = ", ".join(categories)
    return (
        f"Topic definitions:\n{defs}\n\n"
        f"{RULE2}\n\n"
        f"Valid codes: {codes}\n\n"
        f"Document:\n{card_text.strip()}\n\n"
        f"Topic code:"
    )


# ── Ollama helpers ───────────────────────────────────────────────────────────

def warmup_model(model: str, num_ctx: int, ollama_options: dict) -> None:
    """Block until the model is loaded with the exact runtime options, or raise."""
    # Must use same num_ctx + ollama_options as inference calls: different options
    # cause Ollama to restart the model runner, producing another load timeout.
    opts = {"num_predict": 1, "num_ctx": num_ctx, **ollama_options}
    print(f"Waiting for {model} to load", end="", flush=True)
    for attempt in range(_WARMUP_ATTEMPTS):
        try:
            ollama.generate(model=model, prompt=".", options=opts, keep_alive="60m")
            print(" ready.")
            return
        except (ollama.ResponseError, httpx.RemoteProtocolError,
                httpx.ConnectError, httpx.ReadError):
            print(".", end="", flush=True)
            time.sleep(_WARMUP_BACKOFF_S)
    print()
    raise RuntimeError(f"Model {model} did not become ready after "
                       f"{_WARMUP_ATTEMPTS * _WARMUP_BACKOFF_S}s")


# ── Ollama call ───────────────────────────────────────────────────────────────

def classify_card(card_text: str, categories: dict,
                  model: str, temperature: float, num_ctx: int,
                  ollama_options: dict | None = None) -> dict:
    """
    Returns a dict with keys:
      predicted_label, raw_output, elapsed_s,
      prompt_tokens, output_tokens, total_duration_ms, load_duration_ms
    """
    prompt = build_prompt(card_text, categories)
    if "qwen3" in model.lower():
        prompt += " /no_think"
    t0 = time.perf_counter()
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            resp = ollama.generate(
                model=model,
                prompt=prompt,
                system=SYSTEM,
                options={"temperature": temperature, "num_ctx": num_ctx,
                         **(ollama_options or {})},
                keep_alive="60m",
            )
            break
        except (ollama.ResponseError, httpx.RemoteProtocolError,
                httpx.ConnectError, httpx.ReadError) as e:
            if attempt < _RETRY_ATTEMPTS - 1:
                print(f"  [retry {attempt+1}/{_RETRY_ATTEMPTS-1}] {type(e).__name__}: {e} — waiting {_RETRY_BACKOFF_S}s",
                      file=sys.stderr)
                time.sleep(_RETRY_BACKOFF_S)
            else:
                raise
    elapsed = time.perf_counter() - t0

    raw = resp.response          # verbatim, before any parsing

    def _strip_punct(s: str) -> str:
        return s.strip().strip('."\'`*').strip()

    predicted = None
    parse_method = "failed"
    parse_candidates = None

    # (1a) Whole-response exact match
    normalized = _strip_punct(raw.lower())
    if normalized in VALID_CODES:
        predicted = normalized
        parse_method = "exact"
    else:
        # (1b) Last non-empty line exact match
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if lines:
            last = _strip_punct(lines[-1].lower())
            if last in VALID_CODES:
                predicted = last
                parse_method = "exact_lastline"

    # (2) Ambiguity-aware substring fallback
    if predicted is None:
        full_lower = raw.lower()
        last_pos = {}
        for code in VALID_CODES:
            pos = full_lower.rfind(code)
            if pos != -1:
                last_pos[code] = pos
        distinct = list(last_pos)
        if len(distinct) == 1:
            predicted = distinct[0]
            parse_method = "substring"
        elif len(distinct) > 1:
            predicted = max(last_pos, key=last_pos.get)
            parse_method = "substring_ambiguous"
            parse_candidates = "|".join(sorted(distinct))
        # else: predicted=None, parse_method="failed"

    return {
        "predicted_label": predicted,
        "parse_method": parse_method,
        "parse_candidates": parse_candidates,
        "raw_output": raw,
        "elapsed_s": elapsed,
        "prompt_tokens": getattr(resp, "prompt_eval_count", None),
        "output_tokens": getattr(resp, "eval_count", None),
        "total_duration_ms": (resp.total_duration / 1e6
                               if getattr(resp, "total_duration", None) else None),
        "load_duration_ms": (resp.load_duration / 1e6
                              if getattr(resp, "load_duration", None) else None),
    }


# ── CSV writer ────────────────────────────────────────────────────────────────

def ensure_results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def append_rows(rows: list[dict], path: Path = OUTPUT_CSV):
    exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def _append_failed(record: dict):
    exists = FAILED_CSV.exists()
    with open(FAILED_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def done_doc_ids(path: Path) -> set:
    """Return doc_ids that already have a valid predicted_label in path."""
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    return set(df.loc[df["predicted_label"].notna(), "doc_id"])


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary(rows: list[dict], timings: list[float]):
    total = len(rows)
    parsed = [r for r in rows if r["predicted_label"] is not None]
    parse_rate = len(parsed) / total * 100 if total else 0

    dist = {c: 0 for c in VALID_CODES}
    for r in parsed:
        dist[r["predicted_label"]] = dist.get(r["predicted_label"], 0) + 1

    labeled = [r for r in parsed if r["true_label"] != "unlabeled"]
    agreed = sum(1 for r in labeled if r["predicted_label"] == r["true_label"])
    weak_agreement = agreed / len(labeled) * 100 if labeled else 0
    avg_secs = sum(timings) / len(timings) if timings else 0

    method_counts: dict[str, int] = {}
    for r in rows:
        m = r.get("parse_method", "unknown")
        method_counts[m] = method_counts.get(m, 0) + 1

    ambiguous = [r["doc_id"] for r in rows if r.get("parse_method") == "substring_ambiguous"]

    print(f"\n── Summary ({total} cards) ──────────────────────────────")
    print(f"  Parse rate      : {parse_rate:.1f}%  ({len(parsed)}/{total} valid codes)")
    print(f"  Weak-agreement  : {weak_agreement:.1f}%  (predicted == topic_seed, unlabeled excluded, n={len(labeled)})")
    print(f"  Avg time/card   : {avg_secs:.1f}s")
    print(f"\n  Parse method breakdown:")
    for method in ("exact", "exact_lastline", "substring", "substring_ambiguous", "failed"):
        n = method_counts.get(method, 0)
        if n:
            print(f"    {method:<22} {n:>3}")
    if ambiguous:
        print(f"\n  substring_ambiguous doc_ids (review against codebook):")
        for doc_id in ambiguous:
            print(f"    {doc_id}")
    print(f"\n  Label distribution (all 9 classes):")
    for code, count in dist.items():
        bar = "█" * count
        print(f"    {code:<20} {count:>3}  {bar}")
    print()


# ── Modes ─────────────────────────────────────────────────────────────────────

def run_all_dev(cfg: dict, model_override: str | None = None, resume: bool = False):
    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    categories = health_categories(cfg)
    dev_path = health_dev_path(cfg)

    df = pd.read_csv(dev_path).sort_values("doc_id").reset_index(drop=True)

    ensure_results_dir()
    if resume:
        done = done_doc_ids(OUTPUT_CSV)
        if done:
            print(f"Resuming — skipping {len(done)} already-classified cards")
        df = df[~df["doc_id"].isin(done)]

    rows = []
    timings = []
    ts = datetime.now(timezone.utc).isoformat()

    warmup_model(model, num_ctx, ollama_options)
    print(f"Classifying {len(df)} dev cards in doc_id order using {model} "
          f"(options: {ollama_options}) …\n")

    for _, row in df.iterrows():
        doc_id = row["doc_id"]
        card_text = row["card_text"]
        true_label = row.get("topic_seed", "")

        result = classify_card(card_text, categories, model, temperature, num_ctx, ollama_options)
        timings.append(result["elapsed_s"])
        predicted = result["predicted_label"]
        status = predicted if predicted else f"PARSE_ERROR({result['raw_output'][:40]!r})"
        print(f"  {doc_id}: {true_label!r} → {status}  ({result['elapsed_s']:.1f}s)")

        record = {
            "doc_id": doc_id,
            "true_label": true_label,
            "predicted_label": predicted,
            "raw_output": result["raw_output"],
            "parse_method": result["parse_method"],
            "parse_candidates": result["parse_candidates"],
            "method": METHOD,
            "model": model,
            "timestamp": ts,
            "prompt_tokens": result["prompt_tokens"],
            "output_tokens": result["output_tokens"],
            "total_duration_ms": result["total_duration_ms"],
            "load_duration_ms": result["load_duration_ms"],
        }
        append_rows([record])   # write immediately — crash-safe
        if predicted is None:
            _append_failed(record)
        rows.append(record)
        time.sleep(2)           # brief pause between cards — reduces GPU pressure

    print(f"\nWrote {len(rows)} rows → {OUTPUT_CSV}")
    print_summary(rows, timings)


def run_all_gold(cfg: dict, model_override: str | None = None, resume: bool = False):
    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    categories = health_categories(cfg)
    gold_path = PROJECT_ROOT / cfg["health"]["dataset"]["gold_test"]

    safe_model = model.replace(":", "-").replace("/", "-")
    out_path = RESULTS_DIR / f"predictions_zeroshot_{safe_model}_gold.csv"

    df = pd.read_csv(gold_path).sort_values("doc_id").reset_index(drop=True)

    ensure_results_dir()
    if resume:
        done = done_doc_ids(out_path)
        if done:
            print(f"Resuming — skipping {len(done)} already-classified cards")
        df = df[~df["doc_id"].isin(done)]

    rows = []
    timings = []
    ts = datetime.now(timezone.utc).isoformat()

    warmup_model(model, num_ctx, ollama_options)
    print(f"Classifying {len(df)} gold cards in doc_id order using {model} "
          f"(options: {ollama_options}) …\n")

    for _, row in df.iterrows():
        doc_id = row["doc_id"]
        card_text = row["card_text"]
        true_label = row.get("gold_topic", "")

        result = classify_card(card_text, categories, model, temperature, num_ctx, ollama_options)
        timings.append(result["elapsed_s"])
        predicted = result["predicted_label"]
        status = predicted if predicted else f"PARSE_ERROR({result['raw_output'][:40]!r})"
        print(f"  {doc_id}: {true_label!r} → {status}  ({result['elapsed_s']:.1f}s)")

        record = {
            "doc_id": doc_id,
            "true_label": true_label,
            "predicted_label": predicted,
            "raw_output": result["raw_output"],
            "parse_method": result["parse_method"],
            "parse_candidates": result["parse_candidates"],
            "method": METHOD,
            "model": model,
            "timestamp": ts,
            "prompt_tokens": result["prompt_tokens"],
            "output_tokens": result["output_tokens"],
            "total_duration_ms": result["total_duration_ms"],
            "load_duration_ms": result["load_duration_ms"],
        }
        append_rows([record], out_path)
        if predicted is None:
            _append_failed(record)
        rows.append(record)
        time.sleep(2)

    print(f"\nWrote {len(rows)} rows → {out_path}")
    print_summary(rows, timings)


def run_single(card_text: str, cfg: dict, doc_id: str = "ad-hoc",
               model_override: str | None = None):
    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    categories = health_categories(cfg)

    prompt = build_prompt(card_text, categories)
    print("── Prompt ───────────────────────────────────────────────")
    print(SYSTEM)
    print()
    print(prompt)
    print(f"── Ollama options: {ollama_options} ─────────────────────")

    result = classify_card(card_text, categories, model, temperature, num_ctx, ollama_options)
    print(result["raw_output"])
    print(f"\nParsed label     : {result['predicted_label'] or 'PARSE_ERROR'}")
    print(f"Parse method     : {result['parse_method']}")
    if result["parse_candidates"]:
        print(f"Candidates       : {result['parse_candidates']}")
    print(f"Time             : {result['elapsed_s']:.1f}s")
    print(f"Prompt tokens    : {result['prompt_tokens']}")
    print(f"Output tokens    : {result['output_tokens']}")
    print(f"Total duration   : {result['total_duration_ms']:.0f} ms" if result["total_duration_ms"] else "")
    print(f"Load duration    : {result['load_duration_ms']:.0f} ms" if result["load_duration_ms"] else "")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="HESA brief topic classifier — zero-shot baseline"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-dev", action="store_true",
                       help="Classify every row of dev.csv in doc_id order")
    group.add_argument("--all-gold", action="store_true",
                       help="Classify every row of gold_test.csv (final scoring only)")
    group.add_argument("--text", type=str, metavar="TEXT",
                       help="Classify a single card supplied as a string")
    group.add_argument("--doc-id", type=str, metavar="ID",
                       help="Classify a single card looked up by doc_id in dev.csv")
    parser.add_argument("--model", type=str, metavar="MODEL",
                        help="Override the model from config (e.g. gemma2:2b, gemma4:e4b)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip doc_ids already present with a valid predicted_label")

    args = parser.parse_args()
    cfg = load_config()

    if args.all_dev:
        run_all_dev(cfg, model_override=args.model, resume=args.resume)

    elif args.all_gold:
        run_all_gold(cfg, model_override=args.model, resume=args.resume)

    elif args.text:
        run_single(args.text, cfg, model_override=args.model)

    elif args.doc_id:
        dev_path = health_dev_path(cfg)
        df = pd.read_csv(dev_path)
        matches = df[df["doc_id"] == args.doc_id]
        if matches.empty:
            print(f"Error: doc_id {args.doc_id!r} not found in {dev_path}", file=sys.stderr)
            sys.exit(1)
        row = matches.iloc[0]
        run_single(row["card_text"], cfg, doc_id=args.doc_id, model_override=args.model)


if __name__ == "__main__":
    main()
