# My Project: Canadian Health-Policy Brief Classification (not recipes)

This repo is the instructor's course scaffold. My project swaps the recipe
dataset for a corpus of Canadian parliamentary health-policy briefs. These
instructions layer on top of the instructor's CLAUDE.md and win any conflict
for project-specific matters. Never modify instructor code or notebooks —
adapt in my own assignment files and config.

## Data (in data/health/ — synced from a separate corpus repo)

- `train.csv` (258 rows), `dev.csv` (28), `gold_test.csv` (217),
  `corpus.csv` (506, full reference), `SYNC_VERSION` (corpus git tag of origin).
- One row = one document. Model input is ALWAYS the `card_text` column
  (document title + first ~250 words, organization-masked). NEVER add the
  study title, organization name, or filename to any model input — these leak
  the label.
- Labels: `topic_seed` (weak, keyword-derived) in train/dev;
  `gold_topic` (hand-labelled) in gold_test only. `label_source` says which.
- Nine topic codes: public_health, pharmacare, womens_health, workforce,
  childrens_health, mental_health, cancer, indigenous_health, other_none.
  Definitions live in config.yaml categories (copied from my codebook) — use
  those exact definitions in any prompt that describes the classes.
  Substance use / opioids / overdose / addiction = public_health;
  mental_health = mental illness, mood/anxiety, psychiatric services,
  suicide prevention (amended boundary — do not "correct" it).
- Rows with topic_seed=unlabeled are excluded from training and from agreement metrics; they are   rule-recall failures, not other_none.


## Hard rules

- `gold_test.csv` is FROZEN. Never edit it, never train on it, never tune
  prompts or hyperparameters against it. It is scored at final evaluation
  only. `dev.csv` is the tuning set (small — 28 rows; expect noisy scores).
- Data problems get fixed in the corpus repo and re-synced — never patch
  CSVs here. If a fix is needed, tell me; do not do it.
- Class-space rule: every classifier and every evaluation uses ALL NINE
  labels explicitly (pass the full label list to sklearn metrics and model
  heads). mental_health, indigenous_health and cancer have ~0 training rows —
  they exist in gold only. Trained models can't predict them; prompted
  methods can. Do not fold, merge, or drop classes to "fix" this — it is a
  finding, not a bug.
- other_none in gold is scored as its own class (no nine-topic predictor is
  "correct" on it); apply identically to every method.

## Evaluation

- One harness for all methods: takes (predictions, gold), writes
  `results/eval_summary_{method}.json` with identical structure —
  per-class precision/recall/F1/support, accuracy, macro-F1 reported three
  ways: all classes / support ≥ 10 / trainable classes only. Confusion
  matrix saved as CSV + PNG.
- Methods to compare (each gets a row): (1) weak keyword rules (predictions
  = topic_seed applied to gold cards — the floor), (2) sentence embeddings +
  logistic regression, (3) gemma4:12b zero/few-shot via Ollama,
  (4) LoRA fine-tune (Colab, option-A JSONL from weak labels).
- Report the weak-rules row as "scored on the stratified gold set" — the
  gold sample deliberately over-represents hard cases; do not present it as
  corpus-wide rule accuracy.

## Models / environment

- Local model: gemma4:12b via Ollama (RTX 3060 12GB). Always set num_ctx
  (default 4096 is too small); 8k–16k typical. gemma4:e4b is the fast
  fallback for bulk runs. Fine-tuning runs on Colab (upload script in
  scripts/), not locally, unless Unsloth 4-bit on e4b.
- Few-shot examples come from train.csv only, selected without peeking at
  gold; keep prompts + example doc_ids versioned in the assignment files.


## RAG subsystem (added day 13)

- Retrieval corpus: data/health/rag_chunks.jsonl (synced; see SYNC_VERSION).
  Chunks carry UNMASKED text over FULL documents — this deliberately inverts
  two classifier rules: masking (retrieval/citation needs real org names) and
  the card window (retrieval targets content, not primary subject). The
  classifier rules above still bind for anything classification-shaped.
- Index: rag/build_index.py → persistent Chroma in chroma/ (gitignored,
  rebuildable); embedder all-MiniLM-L6-v2 — must match the chunk embedder;
  never mix embedding models within one collection.
- Topic labels are NEVER retrieval filters. Filters are metadata only:
  source_type (the three gap layers), org, stakeholder_type, study, session.
- Generation: gemma4:12b, no num_predict cap (generation, not classification);
  grounded prompt — answer only from passages, cite [doc_id] per claim,
  say so if passages don't contain the answer.
- K: retrieve 5, use top 3 per layer. Not tuned — tuning K against gold or
  demo queries is contamination; K is a stated design constant.
- Evaluation: 10-query known-answer hit-rate@3 + manual faithfulness audit
  of the 8 CMA demo answers; LLM-as-judge at scale = future work.
- Demo path: 8 CMA sections precomputed by script to results/gap_analysis.json;
  the Streamlit tab DISPLAYS that file — only the free-text ask() path is live,
  wrapped in try/except with cached fallback.



## Demo (week 8 / Streamlit)

- Demo document: `demo/` CMA ministerial letter (out-of-distribution on
  purpose). Gap-analysis tab: 8 CMA sections as queries, three retrievals
  filtered by source_type (hesa_brief / hesa_report / gov_response), status
  per ask: echoed / endorsed / committed / unaddressed.
- Precompute anything slower than ~2s (embeddings to .npy, eval JSONs,
  gap-analysis results); the app loads artifacts, it does not compute.
- Wrap all Ollama calls in try/except with cached fallback output so the
  recorded demo cannot die on a model hiccup.

## Session habits

- One session = one repo. Corpus repo is upstream and now quiet.
- End each session: run the relevant eval or smoke test, commit, and append
  one dated line to ../canhealth-corpus/decisions.md (or note it for me).
- Day-13 task (do not do early): kappa relabel of second_pass_sheet.csv
  against the AMENDED codebook; compute cohen_kappa_score; report only —
  never modify gold from it.
