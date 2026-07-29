"""
RAG-augmented classifier for HESA gold cards.

Runs all 217 gold cards through:
  embed card → retrieve 5 from ChromaDB → build prompt with
  4 fixed anchors + up to 5 dynamic examples + card_text → classify via Ollama.

Run:
    export OLLAMA_HOST=http://100.85.195.54:11434
    uv run --no-sync python retrieval/rag_classify.py --all-gold [--model gemma4:12b] [--resume]
"""

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import ollama
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.vector_store import HealthVectorStore

CONFIG_PATH = PROJECT_ROOT / "src" / "baseline_recipe_classifier" / "config.yaml"
RESULTS_DIR = PROJECT_ROOT / "results"
ANCHORS_PATH = PROJECT_ROOT / "retrieval" / "boundary_anchors.yaml"
CORPUS_PATH = PROJECT_ROOT / "data" / "health" / "corpus.csv"
GOLD_PATH = PROJECT_ROOT / "data" / "health" / "gold_test.csv"

OUTPUT_COLS = [
    "doc_id", "true_label", "predicted_label", "raw_output",
    "parse_method", "parse_candidates",
    "method", "model", "timestamp",
    "prompt_tokens", "output_tokens", "total_duration_ms", "load_duration_ms",
]

VALID_CODES = [
    "public_health", "pharmacare", "womens_health", "workforce",
    "childrens_health", "mental_health", "cancer", "indigenous_health",
    "other_none",
]

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

_RETRY_ATTEMPTS = 4
_RETRY_BACKOFF_S = 30
_WARMUP_ATTEMPTS = 48
_WARMUP_BACKOFF_S = 5


# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def health_model(cfg, model_override=None):
    name = model_override or cfg["health"]["default_model"]
    models = cfg["health"]["models"]
    if name not in models:
        raise ValueError(f"Model {name!r} not in config. Known: {list(models)}")
    m = models[name]
    return name, m["temperature"], m["num_ctx"], dict(m.get("ollama_options", {}))


def health_categories(cfg):
    return {
        code: info["description"].strip()
        for code, info in cfg["health"]["categories"].items()
    }


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_rag_prompt(card_text: str, categories: dict,
                     anchors: list[dict], dynamic_examples: list[dict]) -> str:
    codes = ", ".join(categories)
    defs = "\n".join(f"{code}: {desc}" for code, desc in categories.items())

    lines = ["Here are example documents with their topic labels:\n"]

    for ex in anchors:
        lines.append(f"Label: {ex['label']}")
        lines.append(f"Document: {ex['card_text'][:400]}\n")

    for ex in dynamic_examples:
        lines.append(f"Label: {ex['label']}")
        lines.append(f"Document: {ex['card_text'][:400]}\n")

    lines.append(f"Topic definitions:\n{defs}\n")
    lines.append(f"{RULE2}\n")
    lines.append(f"Valid codes: {codes}\n")
    lines.append(f"Document:\n{card_text.strip()}\n")
    lines.append("Topic code:")

    return "\n".join(lines)


# ── Ollama helpers ─────────────────────────────────────────────────────────────

def warmup_model(model, num_ctx, ollama_options):
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


def _strip_punct(s: str) -> str:
    return s.strip().strip('."\'`*').strip()


def parse_response(raw: str) -> tuple[str | None, str, str | None]:
    """Return (predicted_label, parse_method, parse_candidates)."""
    normalized = _strip_punct(raw.lower())
    if normalized in VALID_CODES:
        return normalized, "exact", None

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if lines:
        last = _strip_punct(lines[-1].lower())
        if last in VALID_CODES:
            return last, "exact_lastline", None

    full_lower = raw.lower()
    last_pos = {}
    for code in VALID_CODES:
        pos = full_lower.rfind(code)
        if pos != -1:
            last_pos[code] = pos
    distinct = list(last_pos)
    if len(distinct) == 1:
        return distinct[0], "substring", None
    elif len(distinct) > 1:
        best = max(last_pos, key=last_pos.get)
        candidates = "|".join(sorted(distinct))
        return best, "substring_ambiguous", candidates

    return None, "failed", None


def classify_rag(prompt: str, model: str, temperature: float,
                 num_ctx: int, ollama_options: dict) -> dict:
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
                print(f"  [retry {attempt+1}] {type(e).__name__}: {e} — waiting {_RETRY_BACKOFF_S}s",
                      file=sys.stderr)
                time.sleep(_RETRY_BACKOFF_S)
            else:
                raise
    elapsed = time.perf_counter() - t0

    raw = resp.response
    predicted, parse_method, parse_candidates = parse_response(raw)

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

def append_row(record: dict, path: Path):
    exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def done_doc_ids(path: Path) -> set:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    return set(df.loc[df["predicted_label"].isin(VALID_CODES), "doc_id"])


def failed_doc_ids(path: Path) -> list[str]:
    """Return doc_ids whose best row is still failed after deduping (prefer non-failed, keep first)."""
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if "parse_method" in df.columns:
        df = df.sort_values(
            "parse_method",
            key=lambda s: s.map(lambda v: 0 if v != "failed" else 1),
        )
    df = df.drop_duplicates(subset="doc_id", keep="first")
    bad = df[df["predicted_label"].isna() | ~df["predicted_label"].isin(VALID_CODES)]
    return bad["doc_id"].tolist()


# ── Main run ──────────────────────────────────────────────────────────────────

def run_all_gold(cfg, model_override=None, resume=False):
    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    categories = health_categories(cfg)
    safe_model = model.replace(":", "-").replace("/", "-")
    out_path = RESULTS_DIR / f"predictions_rag_{safe_model}_gold.csv"
    method = f"rag_{safe_model}"

    anchors = yaml.safe_load(open(ANCHORS_PATH))

    corpus_df = pd.read_csv(CORPUS_PATH)
    topic_seed_lookup = dict(zip(corpus_df["doc_id"], corpus_df["topic_seed"]))

    gold_df = pd.read_csv(GOLD_PATH).sort_values("doc_id").reset_index(drop=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if resume:
        done = done_doc_ids(out_path)
        if done:
            print(f"Resuming — skipping {len(done)} already-classified cards")
        gold_df = gold_df[~gold_df["doc_id"].isin(done)]

    store = HealthVectorStore()
    if store.count() == 0:
        print("WARNING: vector store is empty. Index corpus first.", file=sys.stderr)
        print("Run: uv run --no-sync python -c \"import pandas as pd; from retrieval.vector_store import HealthVectorStore; store=HealthVectorStore(); df=pd.read_csv('data/health/corpus.csv'); store.add_batch(df[['doc_id','card_text']].to_dict('records')); print(store.count(), 'cards indexed')\"",
              file=sys.stderr)
        sys.exit(1)

    warmup_model(model, num_ctx, ollama_options)
    print(f"Classifying {len(gold_df)} gold cards (RAG) using {model} …\n")

    ts = datetime.now(timezone.utc).isoformat()
    timings = []

    for _, row in gold_df.iterrows():
        doc_id = row["doc_id"]
        card_text = row["card_text"]
        true_label = row.get("gold_topic", "")

        retrieved = store.query(card_text, n_results=5)
        dynamic_examples = []
        for hit in retrieved:
            seed = topic_seed_lookup.get(hit["doc_id"], "unlabeled")
            if seed == "unlabeled" or seed not in VALID_CODES:
                continue
            dynamic_examples.append({"label": seed, "card_text": hit["card_text"]})

        prompt = build_rag_prompt(card_text, categories, anchors, dynamic_examples)
        result = classify_rag(prompt, model, temperature, num_ctx, ollama_options)
        timings.append(result["elapsed_s"])

        predicted = result["predicted_label"]
        status = predicted if predicted else f"PARSE_FAIL({result['raw_output'][:40]!r})"
        dyn_count = len(dynamic_examples)
        print(f"  {doc_id}: {true_label!r} → {status}  "
              f"({dyn_count} dynamic, {result['elapsed_s']:.1f}s)")

        record = {
            "doc_id": doc_id,
            "true_label": true_label,
            "predicted_label": predicted,
            "raw_output": result["raw_output"],
            "parse_method": result["parse_method"],
            "parse_candidates": result["parse_candidates"],
            "method": method,
            "model": model,
            "timestamp": ts,
            "prompt_tokens": result["prompt_tokens"],
            "output_tokens": result["output_tokens"],
            "total_duration_ms": result["total_duration_ms"],
            "load_duration_ms": result["load_duration_ms"],
        }
        append_row(record, out_path)
        time.sleep(2)

    avg_s = sum(timings) / len(timings) if timings else 0
    print(f"\nWrote {len(gold_df)} rows → {out_path}")
    print(f"Average time/card: {avg_s:.1f}s")


# ── Retry-failed mode ─────────────────────────────────────────────────────────

def run_retry_failed(predictions_path: str, num_predict_override: int,
                     cfg, model_override=None):
    pred_path = Path(predictions_path)
    if not pred_path.exists():
        print(f"Error: {pred_path} not found", file=sys.stderr)
        sys.exit(1)

    failed_ids = failed_doc_ids(pred_path)
    if not failed_ids:
        print("No failed doc_ids found — nothing to retry.")
        return

    print(f"Failed doc_ids to retry ({len(failed_ids)}):")
    for did in failed_ids:
        print(f"  {did}")
    print()

    model, temperature, num_ctx, ollama_options = health_model(cfg, model_override)
    retry_options = {**ollama_options, "num_predict": num_predict_override}
    categories = health_categories(cfg)
    safe_model = model.replace(":", "-").replace("/", "-")
    retry_method = f"rag_{safe_model}_retry{num_predict_override}"

    anchors = yaml.safe_load(open(ANCHORS_PATH))
    corpus_df = pd.read_csv(CORPUS_PATH)
    topic_seed_lookup = dict(zip(corpus_df["doc_id"], corpus_df["topic_seed"]))
    gold_df = pd.read_csv(GOLD_PATH).set_index("doc_id")

    store = HealthVectorStore()
    ts = datetime.now(timezone.utc).isoformat()

    warmup_model(model, num_ctx, retry_options)
    print(f"Retrying {len(failed_ids)} cards with num_predict={num_predict_override} …\n")

    results = []
    for doc_id in failed_ids:
        if doc_id not in gold_df.index:
            print(f"  {doc_id}: NOT FOUND in gold_test.csv — skipping", file=sys.stderr)
            continue

        card_text = gold_df.loc[doc_id, "card_text"]
        true_label = gold_df.loc[doc_id, "gold_topic"]

        retrieved = store.query(card_text, n_results=5)
        dynamic_examples = []
        for hit in retrieved:
            seed = topic_seed_lookup.get(hit["doc_id"], "unlabeled")
            if seed == "unlabeled" or seed not in VALID_CODES:
                continue
            dynamic_examples.append({"label": seed, "card_text": hit["card_text"]})

        prompt = build_rag_prompt(card_text, categories, anchors, dynamic_examples)
        result = classify_rag(prompt, model, temperature, num_ctx, retry_options)
        predicted = result["predicted_label"]
        status = predicted if predicted else f"STILL_FAILED (output_tokens={result['output_tokens']})"
        print(f"  {doc_id}: {true_label!r} → {status}  "
              f"(output_tokens={result['output_tokens']}, {result['elapsed_s']:.1f}s)")

        record = {
            "doc_id": doc_id,
            "true_label": true_label,
            "predicted_label": predicted,
            "raw_output": result["raw_output"],
            "parse_method": result["parse_method"],
            "parse_candidates": result["parse_candidates"],
            "method": retry_method,
            "model": model,
            "timestamp": ts,
            "prompt_tokens": result["prompt_tokens"],
            "output_tokens": result["output_tokens"],
            "total_duration_ms": result["total_duration_ms"],
            "load_duration_ms": result["load_duration_ms"],
        }
        append_row(record, pred_path)
        results.append(record)

    n_resolved = sum(1 for r in results if r["predicted_label"] is not None)
    n_still_failed = len(results) - n_resolved
    print(f"\nRetry complete: {n_resolved}/{len(results)} resolved, "
          f"{n_still_failed} still failed.")
    print(f"Rows appended to {pred_path}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RAG-augmented HESA classifier"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-gold", action="store_true",
                       help="Classify all 217 gold cards")
    group.add_argument("--retry-failed", action="store_true",
                       help="Re-classify failed doc_ids from --predictions using a higher num_predict")
    parser.add_argument("--predictions", type=str, metavar="PATH",
                        help="Predictions CSV to read failed doc_ids from (--retry-failed only)")
    parser.add_argument("--num-predict-override", type=int, metavar="N",
                        help="num_predict to use for retry pass (--retry-failed only)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model override (e.g. gemma4:12b)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip doc_ids already present with a valid predicted_label")
    args = parser.parse_args()

    cfg = load_config()

    if args.retry_failed:
        if not args.predictions:
            parser.error("--retry-failed requires --predictions PATH")
        if not args.num_predict_override:
            parser.error("--retry-failed requires --num-predict-override N")
        run_retry_failed(args.predictions, args.num_predict_override, cfg,
                         model_override=args.model)
    else:
        run_all_gold(cfg, model_override=args.model, resume=args.resume)


if __name__ == "__main__":
    main()
