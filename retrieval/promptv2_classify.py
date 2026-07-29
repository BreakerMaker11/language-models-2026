#!/usr/bin/env python3
"""
HESA Health-Policy Brief Classifier — Week 4 prompt-v2 (sharpened definitions + RULE3).

Identical to main.py except:
  - womens_health and other_none definitions sharpened in config.yaml (shared)
  - RULE3 decision rule injected into every prompt
  - --eval-prompt mode for fast iteration on a hand-labeled eval set
  - Output method name: promptv2_gemma4-12b
  - main.py is NOT modified

Modes:
  --all-dev          classify every row of dev.csv in doc_id order
  --all-gold         classify every row of gold_test.csv
  --eval-prompt PATH classify a hand-labeled CSV (doc_id, card_text, gold_topic)
  --text "..."       classify a single card text supplied on the command line
  --doc-id ID        classify a single card looked up by doc_id in dev.csv
  --retry-failed     re-classify failed doc_ids from --predictions
"""

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_RETRY_ATTEMPTS = 4
_RETRY_BACKOFF_S = 30
_WARMUP_ATTEMPTS = 48
_WARMUP_BACKOFF_S = 5

import httpx
import ollama
import pandas as pd
import yaml

# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "src" / "baseline_recipe_classifier" / "config.yaml"
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_COLS = [
    "doc_id", "true_label", "predicted_label", "raw_output",
    "parse_method", "parse_candidates",
    "method", "model", "timestamp",
    "prompt_tokens", "output_tokens", "total_duration_ms", "load_duration_ms",
]
FAILED_CSV = RESULTS_DIR / "failed_cards_promptv2.csv"

METHOD = "promptv2_gemma4-12b"

VALID_CODES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health",
    "other_none",
]

# ── Config loading ────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def health_model(cfg, model_override: str | None = None):
    name = model_override or cfg["health"]["default_model"]
    models = cfg["health"]["models"]
    if name not in models:
        raise ValueError(f"Model {name!r} not in config health.models. "
                         f"Known: {list(models)}")
    m = models[name]
    return name, m["temperature"], m["num_ctx"], dict(m.get("ollama_options", {}))


def health_categories(cfg):
    return {
        code: info["description"].strip()
        for code, info in cfg["health"]["categories"].items()
    }


def health_dev_path(cfg):
    rel = cfg["health"]["dataset"]["dev"]
    return PROJECT_ROOT / rel


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

RULE3 = (
    "Decision rule: if a document frames vaccine policy or public health measures "
    "primarily in terms of personal freedom, civil liberties, or individual rights "
    "— rather than as population-level health policy — classify it as other_none, "
    "regardless of whether vaccine or illness terms appear."
)


def build_prompt(card_text: str, categories: dict) -> str:
    codes = ", ".join(categories)
    defs = "\n".join(f"{code}: {desc}" for code, desc in categories.items())
    return (
        f"Topic definitions:\n{defs}\n\n"
        f"{RULE2}\n\n"
        f"{RULE3}\n\n"
        f"Valid codes: {codes}\n\n"
        f"Document:\n{card_text.strip()}\n\n"
        f"Topic code:"
    )


# ── Ollama helpers ───────────────────────────────────────────────────────────

def warmup_model(model: str, num_ctx: int, ollama_options: dict) -> None:
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

    raw = resp.response

    def _strip_punct(s: str) -> str:
        return s.strip().strip('."\'`*').strip()

    predicted = None
    parse_method = "failed"
    parse_candidates = None

    normalized = _strip_punct(raw.lower())
    if normalized in VALID_CODES:
        predicted = normalized
        parse_method = "exact"
    else:
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if lines:
            last = _strip_punct(lines[-1].lower())
            if last in VALID_CODES:
                predicted = last
                parse_method = "exact_lastline"

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


# ── CSV helpers ───────────────────────────────────────────────────────────────

def ensure_results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def append_rows(rows: list[dict], path: Path):
    exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def done_doc_ids(path: Path) -> set:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    return set(df.loc[df["predicted_label"].notna(), "doc_id"])


# ── Modes ─────────────────────────────────────────────────────────────────────

def _classify_dataframe(df: pd.DataFrame, true_label_col: str,
                        out_path: Path, cfg: dict,
                        model_override: str | None, resume: bool) -> None:
    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    categories = health_categories(cfg)
    ensure_results_dir()

    if resume:
        done = done_doc_ids(out_path)
        if done:
            print(f"Resuming — skipping {len(done)} already-classified cards")
        df = df[~df["doc_id"].isin(done)]

    ts = datetime.now(timezone.utc).isoformat()
    warmup_model(model, num_ctx, ollama_options)
    print(f"Classifying {len(df)} cards using {model} (options: {ollama_options}) …\n")

    for _, row in df.iterrows():
        doc_id = row["doc_id"]
        card_text = row["card_text"]
        true_label = row.get(true_label_col, "")

        result = classify_card(card_text, categories, model, temperature,
                               num_ctx, ollama_options)
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
        time.sleep(2)

    print(f"\nWrote results → {out_path}")


def run_all_dev(cfg, model_override=None, resume=False):
    df = pd.read_csv(PROJECT_ROOT / cfg["health"]["dataset"]["dev"])
    df = df.sort_values("doc_id").reset_index(drop=True)
    out_path = RESULTS_DIR / "predictions_promptv2_gemma4-12b_dev.csv"
    _classify_dataframe(df, "topic_seed", out_path, cfg, model_override, resume)


def run_all_gold(cfg, model_override=None, resume=False):
    df = pd.read_csv(PROJECT_ROOT / cfg["health"]["dataset"]["gold_test"])
    df = df.sort_values("doc_id").reset_index(drop=True)
    out_path = RESULTS_DIR / "predictions_promptv2_gemma4-12b_gold.csv"
    _classify_dataframe(df, "gold_topic", out_path, cfg, model_override, resume)


def run_eval_prompt(eval_path: str, cfg, model_override=None, resume=False):
    """Classify a hand-labeled prompt_eval CSV for fast prompt iteration."""
    df = pd.read_csv(eval_path)
    if "card_text" not in df.columns or "doc_id" not in df.columns:
        print(f"Error: {eval_path} must have doc_id and card_text columns", file=sys.stderr)
        sys.exit(1)
    true_label_col = "gold_topic" if "gold_topic" in df.columns else "true_label"
    out_path = RESULTS_DIR / "predictions_promptv2_gemma4-12b_prompteval.csv"
    _classify_dataframe(df, true_label_col, out_path, cfg, model_override, resume)
    print(f"\nTo score:\n"
          f"  uv run --no-sync python -m eval.harness \\\n"
          f"    --predictions {out_path} \\\n"
          f"    --method promptv2_gemma4-12b_prompteval \\\n"
          f"    --gold {eval_path}")


def run_single(card_text: str, cfg, doc_id: str = "ad-hoc", model_override=None):
    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    categories = health_categories(cfg)

    prompt = build_prompt(card_text, categories)
    print("── Prompt ───────────────────────────────────────────────")
    print(SYSTEM)
    print()
    print(prompt)
    print(f"── Ollama options: {ollama_options} ─────────────────────")

    result = classify_card(card_text, categories, model, temperature,
                           num_ctx, ollama_options)
    print(result["raw_output"])
    print(f"\nParsed label  : {result['predicted_label'] or 'PARSE_ERROR'}")
    print(f"Parse method  : {result['parse_method']}")
    if result["parse_candidates"]:
        print(f"Candidates    : {result['parse_candidates']}")
    print(f"Time          : {result['elapsed_s']:.1f}s")


def _failed_doc_ids(predictions_path: Path) -> list[str]:
    df = pd.read_csv(predictions_path)
    if "parse_method" in df.columns:
        df = df.sort_values(
            "parse_method",
            key=lambda s: s.map(lambda v: 0 if v != "failed" else 1),
        )
    df = df.drop_duplicates(subset="doc_id", keep="first")
    bad = df[df["predicted_label"].isna() | ~df["predicted_label"].isin(VALID_CODES)]
    return bad["doc_id"].tolist()


def run_retry_failed(predictions_path: str, num_predict_override: int,
                     cfg, model_override=None):
    pred_path = Path(predictions_path)
    if not pred_path.exists():
        print(f"Error: {pred_path} not found", file=sys.stderr)
        sys.exit(1)

    failed_ids = _failed_doc_ids(pred_path)
    if not failed_ids:
        print("No failed doc_ids found — nothing to retry.")
        return

    print(f"Failed doc_ids to retry ({len(failed_ids)}):")
    for did in failed_ids:
        print(f"  {did}")

    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    retry_options = {**ollama_options, "num_predict": num_predict_override}
    categories = health_categories(cfg)
    gold_path = PROJECT_ROOT / cfg["health"]["dataset"]["gold_test"]
    gold_df = pd.read_csv(gold_path).set_index("doc_id")

    ts = datetime.now(timezone.utc).isoformat()
    warmup_model(model, num_ctx, retry_options)
    print(f"\nRetrying {len(failed_ids)} cards with num_predict={num_predict_override} …\n")

    for doc_id in failed_ids:
        if doc_id not in gold_df.index:
            print(f"  {doc_id}: NOT FOUND in gold_test.csv — skipping", file=sys.stderr)
            continue
        card_text = gold_df.loc[doc_id, "card_text"]
        true_label = gold_df.loc[doc_id, "gold_topic"]

        result = classify_card(card_text, categories, model, temperature,
                               num_ctx, retry_options)
        predicted = result["predicted_label"]
        print(f"  {doc_id}: {true_label!r} → {predicted or 'STILL_FAILED'}  "
              f"({result['elapsed_s']:.1f}s)")

        record = {
            "doc_id": doc_id, "true_label": true_label,
            "predicted_label": predicted,
            "raw_output": result["raw_output"],
            "parse_method": result["parse_method"],
            "parse_candidates": result["parse_candidates"],
            "method": f"{METHOD}_retry{num_predict_override}",
            "model": model, "timestamp": ts,
            "prompt_tokens": result["prompt_tokens"],
            "output_tokens": result["output_tokens"],
            "total_duration_ms": result["total_duration_ms"],
            "load_duration_ms": result["load_duration_ms"],
        }
        append_rows([record], pred_path)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="HESA classifier — prompt-v2 (sharpened definitions + RULE3)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-dev", action="store_true")
    group.add_argument("--all-gold", action="store_true")
    group.add_argument("--eval-prompt", type=str, metavar="PATH",
                       help="Hand-labeled CSV (doc_id, card_text, gold_topic) for prompt iteration")
    group.add_argument("--text", type=str, metavar="TEXT")
    group.add_argument("--doc-id", type=str, metavar="ID")
    group.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--predictions", type=str, metavar="PATH")
    parser.add_argument("--num-predict-override", type=int, metavar="N")
    parser.add_argument("--model", type=str, metavar="MODEL")
    parser.add_argument("--resume", action="store_true")

    args = parser.parse_args()
    cfg = load_config()

    if args.retry_failed:
        if not args.predictions:
            parser.error("--retry-failed requires --predictions PATH")
        if not args.num_predict_override:
            parser.error("--retry-failed requires --num-predict-override N")
        run_retry_failed(args.predictions, args.num_predict_override, cfg,
                         model_override=args.model)
    elif args.all_dev:
        run_all_dev(cfg, model_override=args.model, resume=args.resume)
    elif args.all_gold:
        run_all_gold(cfg, model_override=args.model, resume=args.resume)
    elif args.eval_prompt:
        run_eval_prompt(args.eval_prompt, cfg, model_override=args.model,
                        resume=args.resume)
    elif args.text:
        run_single(args.text, cfg, model_override=args.model)
    elif args.doc_id:
        dev_path = PROJECT_ROOT / cfg["health"]["dataset"]["dev"]
        df = pd.read_csv(dev_path)
        matches = df[df["doc_id"] == args.doc_id]
        if matches.empty:
            print(f"Error: doc_id {args.doc_id!r} not found in {dev_path}", file=sys.stderr)
            sys.exit(1)
        run_single(matches.iloc[0]["card_text"], cfg, doc_id=args.doc_id,
                   model_override=args.model)


if __name__ == "__main__":
    main()
