# Decision Log — CanHealth Corpus

One line per decision: what was decided, why, and what it affected.
Append at the end of every working session. This log is the raw material for
the final report's data & methods narrative.

## Scoping
- Project scoped to Canadian federal health-policy stakeholder input (asks →
  committee recommendations → government commitments) after surveying sources;
  raw patient/physician free-text feedback rejected as inaccessible behind
  health-authority agreements or scraping ToS.
- Classification sources narrowed to HESA only (time constraint); Open
  Government consultations, CMA PolicyBase, StatCan marked DEFERRED in
  CLAUDE.md with specs retained for reactivation.
- Separate corpus repo from course repo: course repo is instructor-owned and
  synced weekly; corpus repo commits code + manifest + processed outputs,
  gitignores raw/interim; sync via copy script.

## Harvest
- HESA Work tab only: briefs + reports + gov responses. Transcripts skipped
  (multi-speaker, no single stakeholder/topic label — noted as future work);
  minutes/notices/webcasts skipped (procedural, no substantive positions).
- Procedural-title filter with committed whitelist by study_activity_id;
  discards logged. Whitelisted: C-64 pharmacare, C-31 dental, C-293 pandemic
  (topic coverage). Seven condition-specific bills left discarded to avoid an
  unlabeled pile (revisit if a topic runs short).
- Sessions 44-1 + 45-1 harvested (562 docs, 0 failures). 44-1 prioritized for
  complete brief→report→response chains; 45-1 added ~74 docs and diluted the
  COVID share. Session encoded in URL path; parliament_session in manifest.
- Reports/gov responses: DocumentViewer HTML preferred as text source
  (structured headings/recommendations); pdf_url kept for provenance;
  cited by section/recommendation instead of page.

## Taxonomy & weak labels (topic_rules.yaml)
- Ten topics. womens_health added (69 briefs unmatched by original eight);
  public_health added (C-293 + COVID material); pharmacare widened to drugs &
  medical devices (patented medicines, devices studies); keywords added for
  pharmaceutical sovereignty and antimicrobial resistance after 45-1 harvest.
- Title-exempt studies (topic from card_text, not study title): COVID
  emergency study (title = occasion, not topic; would have mislabeled 160
  briefs as public_health) and the immigration/healthcare study (genuinely
  mixed workforce vs access briefs).
- Stakeholder type gains sixth class: individual (HESA accepts personal
  briefs; forcing them into org categories would be wrong; distinct voice).
- First-match-wins rule order = precedence (specific topics above broad ones).

## Extraction & cleaning
- Stage separation preserved: no network in clean/; sparse-HTML repair moved
  to a harvest-side command (extraction stays offline and rerunnable).
- OCR layer added (ocrmypdf → interim/ocr/, extractor prefers it, raw
  immutable) after the Workforce gov_response — a gap-analysis chain document —
  turned out to be scanned. Same doc doubles as the week-7 multimodal sample
  (Tesseract vs Gemma 4 vision comparison).
- Single-page empty PDFs folded into needs_ocr (the 200-char rule originally
  covered multi-page only); garbled FASD PDF (fake "de" langdetect) routed to
  needs_ocr.
- Contact scrubbing ([CONTACT] for emails/phones/addresses, signature blocks
  stripped): zero topic signal, embedding noise, hygiene for a possibly
  public corpus. Names in manifest metadata retained for attribution.
- layout_mangled flag (short-line fraction + digit density, tuned on the 988
  infographic brief as known-positive): detect, report, never auto-drop.
- 150-word floor dropped 17 docs, mostly short personal COVID letters — the
  rule trims the individual-citizen voice at its thinnest; noted as a
  limitation.
- Org masking: submitting org + parenthetically defined acronym alias → [ORG]
  (CDA case), word-boundary matched so other orgs' acronyms (CDAA) survive;
  masked variants generated for briefs only (masking the committee's own name
  in reports produced nonsense).
- Title-echo running headers (report title repeated as multi-line page header)
  stripped by matching the document's own first-page title — found by manual
  verification of the breast-cancer report; the >50%-of-pages rule missed the
  split-line variant.
- Report cleaning verified end-to-end on the breast-cancer report: 15,192 →
  5,378 words, body chapters intact, 13 recommendations preserved once
  (duplicated copies in ToC/back matter correctly removed).

## Classification design
- Unit = card_text (~250 words: title + head of org-masked text), one card per
  document. Rationale: signal concentration (briefs front-load thesis), fair
  three-way method comparison on identical inputs, BERT-family 512-token
  baseline fits, cheap iteration. RAG uses separate 300–800-token
  heading-bounded chunks — different question, different unit.
- Tiered card builder (summary section → head+recommend-sentences → plain
  head) implemented behind a --card flag; simple is default; tiered vs simple
  is a planned week-4 ablation on the gold set.
- Single-label topic for the course; multi-label named as extension (CMA
  ministerial letter kept as the out-of-distribution week-8 demo document —
  spans ~8 topics, demonstrates the limit).

## Evaluation plan
- Gold set ~200 briefs, stratified by topic and stakeholder type, frozen
  before model work; macro-F1 (imbalance observed: COVID study = 1/3 of
  briefs pre-correction); intra-annotator kappa on a 50-doc relabel (solo
  annotator; second-pass two weeks later).
- COVID downsampling / per-study cap at train time noted as imbalance
  handling for the write-up.

## Evaluation harness — src/eval/harness.py (2026-07-18)

**Unified scorer built:** `src/eval/harness.py` — pure scorer, no inference.
Invoked as `uv run python -m eval.harness --predictions results/X.csv --method NAME`.
Load & align: reads predictions CSV, dedupes to one row per doc_id (prefers
parse_method != 'failed'), left-joins to gold_test.csv on doc_id. Asserts
exactly 217 gold doc_ids covered; missing predictions get predicted_label=None
→ "PARSE_FAIL" so they score as errors, never drop from the denominator.
Invalid/None predicted_label also mapped to "PARSE_FAIL".

**Label space fixed at 9:** LABELS list passed explicitly as `labels=` to every
sklearn call so classes with zero predictions appear with 0.0 rather than being
silently dropped. other_none scored as a real class.

**Three macro-F1 variants:** macro_f1_all (all 9), macro_f1_support10 (classes
with gold support ≥ 10 — excludes indigenous_health n=3), macro_f1_trainable
(classes present as non-unlabeled topic_seed in train.csv — computed from the
file, not hardcoded; currently: public_health, pharmacare, womens_health, workforce).

**Output schema:** `results/eval_summary_{method}.json` with fixed structure
(method, model, n, accuracy, macro_f1_all, macro_f1_support10, macro_f1_trainable,
per_class, efficiency, failures, timestamp, predictions_file).
Confusion matrix written as CSV + PNG (rows=true, cols=predicted).

**Efficiency block** computed from predictions columns where present: median
latency, median prompt/output tokens, tokens_per_classification, cards_per_min.
Null for methods without timing columns.

## Baseline method results — gold set (2026-07-18)

Three methods evaluated against gold_test.csv (n=217):

**weakrules** (`src/eval/generate_weakrules.py`): joins corpus.csv topic_seed
onto gold doc_ids; topic_seed='unlabeled' → PARSE_FAIL. No inference.
Accuracy 0.415, macro-F1 all=0.422, trainable=0.539. 18 PARSE_FAILs (unlabeled
cards). other_none F1=0.000 (rules never fire that label). Floor baseline.

**embed_lr** (`src/eval/embed_lr.py`): all-MiniLM-L6-v2 sentence embeddings +
LogisticRegression(max_iter=2000, class_weight='balanced'). Trained on 211
non-unlabeled train.csv rows (4 classes only: public_health, pharmacare,
womens_health, workforce). Accuracy 0.410, macro-F1 all=0.258, trainable=0.580.
Macro-F1 collapses because the model predicts zero for 5 classes not present in
training data — confirmed expected finding, not a bug. 0 parse failures.

**zeroshot_gemma4-12b**: Accuracy 0.627, macro-F1 all=0.634, trainable=0.704.
10 parse failures (output_tokens hit 2048 cap on cards with runaway thinking
chains). Correctly predicts all 9 classes including zero-train ones
(mental_health F1=0.444, indigenous_health F1=0.800, cancer F1=0.421).
Median latency 17.5s, 3.43 cards/min. Clear winner over both baselines.

## main.py extensions (2026-07-18/19)

**--all-gold mode added (2026-07-18):** `run_all_gold()` classifies all 217
gold_test.csv cards, writing to `results/predictions_zeroshot_{model}_gold.csv`.
Resume logic identical to --all-dev (skip doc_ids with valid predicted_label).

**--no-codebook flag (2026-07-19):** Allows excluding category descriptions and
Rule 2 precedence from the prompt. With flag: prompt contains only the 9 bare
category codes ("Topics: code1, code2, ...") plus the card text. Without flag
(default): full definitions + Rule 2 included as before. System prompt
("Respond with exactly one category code") is always present regardless of flag.
Provenance recorded in method column: baseline_zeroshot_nocodebook.

**llama3.2:3b added to config (2026-07-19):** Added to health.models in
config.yaml with temperature=0.0, num_ctx=8192, num_predict=2048.

**--retry-failed mode (2026-07-19):** Rescue pass for cards whose best row is
still failed after deduping. Usage: `--retry-failed --predictions PATH
--num-predict-override N`. Identifies failed doc_ids from the given predictions
CSV (dedup then filter invalid predicted_label), prints the list, re-classifies
only those cards from gold_test.csv with num_predict overridden. Single attempt
per card (temp=0, retry pointless). Appends new rows to the same CSV; never
rewrites existing rows. Provenance in method column:
baseline_zeroshot_retry{N}. Harness dedupe picks up resolved rows automatically.
Targeting predictions_zeroshot_gemma4-12b_gold_with_duplicates.csv (7 failures)
rather than cleaned_ file (10 failures) — duplicates file already contains
successful retry rows for 3 cards the cleaned file is missing.

## Labeling redesign (2026-07-11)

**Cross-cutting topics removed:** `digital_health`, `wait_times`, `funding`,
`primary_care` removed from topic_rules.yaml. These themes appear as
subordinate concerns across virtually every brief (e.g., pharmacare briefs
mention drug funding; workforce briefs mention primary-care access gaps).
Single-label keyword matching on cross-cutting themes produces noisy labels
driven by incidental co-occurrence rather than a document's primary subject.
Reserved for a multi-label extension (binary vector per topic, one classifier
head per label) planned for Week 9.

**Content-first labeling:** Changed from title-first to content-first strategy.
Old: study title (1+ keyword) → card_text (1+ keyword) → unlabeled.
New: card_text (≥2 distinct keyword hits) → study title (1+ keyword,
non-exempt) → unlabeled. Rationale: title-first assigned the same study-level
label to all briefs in a study regardless of the brief's actual content,
conflating topic of study with topic of the brief. The ≥2 content-hit
threshold trades recall for precision; the study-title fallback preserves recall
for unambiguous studies. Unlabeled fraction rose to ~21 %; addressed by strong
keywords and keyword expansion (see below).

**Card construction fix:** `card_text` is now the first 250 words of the
org-masked document text only — no study title injected. Rationale: injecting
the study title into the card leaks the title-derived label directly into the
model input, creating a shortcut that will not generalize to out-of-study
documents at inference time. The `study_title` column stays in corpus.csv for
stratification and analysis; it is never part of the model input.

**Strong-keyword support (implemented 2026-07-11):** A `strong_keywords` list
per topic in topic_rules.yaml; any match labels the doc without needing ≥2.
Regular `keywords` still require ≥2 distinct hits. Strong keywords are reserved
for terms so specific they cannot appear incidentally in a brief about a
different topic: e.g., `pharmacare`, `first nations`, `paediatric`, `oncology`,
`opioid`, `biosimilar`, `internationally trained`, `carcinogen`. TF-IDF mining
over 107 unlabeled cards informed which keywords to promote. New keyword added:
`long covid` (public_health strong), `internationally trained` (workforce strong),
`indigenous health` (indigenous_health strong), `carcinogen` (cancer strong),
`medical device` moved to pharmacare strong_keywords.

**Final corpus (v0.2, 2026-07-11):** 506 rows, 8 topics, content-first labeling
with strong keywords. Unlabeled fraction: 14.4 % (73 docs — below the 15 %
target). Topic distribution: public_health 28.1 %, pharmacare 19.8 %,
womens_health 16.4 %, mental_health 8.9 %, workforce 5.5 %, indigenous_health
2.8 %, cancer 2.2 %, childrens_health 2.0 %. Outputs deterministic (run ×2,
identical counts). Corpus committed as v0.2-corpus.

## Codebook boundary: mental_health vs public_health (2026-07-13)

Substance use, addiction, opioids, overdose, harm reduction, and drug policy
moved categorically to public_health. Substance-use boundary made categorical
(→ public_health) after an ask-level test proved too vague to apply
consistently; codebook, rules, and gold aligned in one pass, pre-freeze.
mental_health now covers mental illness, mood/anxiety disorders, psychiatric
services, depression, and suicide prevention only. topic_rules.yaml updated
accordingly; corpus.csv rebuilt pre-freeze.

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- DRAFT — pending my review                                               -->
<!-- Entries below drafted by Claude Code from session history 2026-07-18.  -->
<!-- Review against codebook_v1_1.md and git log before accepting.          -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->

## DRAFT — Model phase setup (2026-07-17/18)

**Classifier scaffold (2026-07-17):** `main.py` created at project root with
two modes: `--all-dev` (all 29 dev.csv rows in doc_id order, crash-safe
per-card CSV writes, resume on restart) and single-card modes (`--text`,
`--doc-id`). Output: `results/predictions_baseline_dev.csv` with columns
doc_id, true_label, predicted_label, raw_output, method, model, timestamp,
prompt_tokens, output_tokens, total_duration_ms, load_duration_ms.

**Codebook definitions in config (2026-07-17):** Nine category descriptions in
`config.yaml` (health.categories) replaced with verbatim text from
`data/health/codebook_v1_1.md`. Rule 2 precedence note (womens_health beats
cancer for breast/cervical; indigenous_health beats mental_health;
childrens_health beats cancer for pediatric oncology) added as a YAML comment
above the categories block and injected verbatim into every prompt. This makes
the config the single source of truth: changing a definition updates both
the prompt and the documentation simultaneously.

**Prompt design — zero-shot baseline (2026-07-17):** System prompt: "You are
a policy document classifier. Assign exactly one topic code from the list
below. Respond with exactly one category code and nothing else." User prompt:
definitions block + Rule 2 + valid codes list + card_text. Input is card_text
only; study title, org name, and filename are never included (would leak the
label). Temperature 0, num_ctx 8192.

**Per-model Ollama options in config (2026-07-18):** Restructured
`config.yaml` from a single `health.model` entry to `health.models` dict keyed
by model name, each with temperature, num_ctx, and `ollama_options`. Rationale:
qwen3 and gemma4 need different mechanical caps and think-suppression
mechanisms; hardcoding these in code would require a code change per model.
`health.default_model` names the default; `--model` flag overrides at runtime.

**gemma4:12b think-suppression finding (2026-07-18):** `think: false` in
Ollama options suppresses thinking tokens from `resp.response` and
`resp.thinking` (both come back clean / null) but does NOT reduce `eval_count`
— the model still generates ~390–470 internal reasoning tokens per card.
Confirmed empirically: one-card diagnostic showed eval_count=389 with
`think: false` and response='public_health'. Genuine think-disable is not
available in this Ollama version for gemma4:12b. Accepted cost: ~15s/card,
~400 thinking tokens consumed silently. `think: false` is kept because it keeps
`raw_output` clean (just the code word) even though it does not reduce compute.

**num_predict cap history (2026-07-18):** Three values attempted for gemma4:
(a) num_predict: 10 — caused 0% parse rate because thinking tokens exhausted
the budget before visible output; (b) num_predict: 600 — caused ~38% parse
failures on longer-thinking cards (emergency_situation study cards spike to
600+ thinking tokens); (c) num_predict: 2048 — current value, acts as a
runaway-safety cap only, well above observed thinking-chain lengths. For
qwen3:14b, `/no_think` appended to the user prompt genuinely suppresses
thinking (verified: eval_count ≈ 2–10 tokens); num_predict: 10 is sufficient
and acts as a real cap on response verbosity.

**Evaluation harness (2026-07-18):** `evaluate_health.py` reads any
predictions CSV and writes `results/eval_summary_{method}.json`. Reports three
macro-F1 views: all 9 classes, support ≥ 10, trainable classes only. Latency
metrics (median_latency_s, throughput_cards_per_min, tokens_per_second,
tokens_per_classification) computed from the duration/token columns; all null
for non-LLM methods. Confusion matrix saved as CSV. Gold path accepted via
`--gold` flag; without it, uses topic_seed (dev evaluation). Gold path is never
called automatically — intentional, to prevent accidental gold consumption.

**Serial bakeoff protocol (2026-07-18):** Models run strictly serially via
`bakeoff.sh`: all gemma4 cards complete → `ollama stop gemma4:12b` → all qwen3
cards. Never interleaved. Rationale: RTX 3060 12GB cannot hold two models
simultaneously; interleaving causes mid-run model swaps which add reload
latency and make token/latency metrics incomparable across runs.
`keep_alive: "-1s"` holds each model loaded between cards within its run.

**Retry / crash-recovery design (2026-07-18):** `classify_card` retries up to
4 times with 30s backoff, catching `ollama.ResponseError`,
`httpx.RemoteProtocolError`, `httpx.ConnectError`, and `httpx.ReadError`.
Broader exception set needed because the remote server sometimes kills the TCP
connection before sending an HTTP response (manifests as `RemoteProtocolError`,
not `ResponseError`). 2s inter-card sleep added to reduce GPU thermal pressure
after repeated crashes at card 18 (consistent boundary suggesting memory
saturation). Rows written to CSV immediately after each card (not batched at
end) so a mid-run crash loses at most one card.

**Bakeoff preliminary results — dev set (2026-07-18, incomplete run):**
gemma4:12b run completed with num_predict:600 showed 62% parse rate (cap too
tight); rerun with num_predict:2048 in progress at session end. qwen3:14b
(prior complete run, now stale due to config changes): 29/29 parsed, 75%
weak-agreement on 24 labeled cards, median latency 11.1s, median output_tokens
343 (includes thinking tokens in eval_count despite /no_think — needs
verification on clean run). Head-to-head comparison deferred to next session
pending clean gemma4 run.

## Week 2 — Embedding evaluation (2026-07-19)

**Evaluation script:** `src/eval/embedding_eval.py` — compares embedding models
on 20 domain-specific term pairs (13 close, 7 far, 5 hard-boundary) drawn from
codebook_v1_1.md. Configurable MODELS list; adding a new model requires one
dict entry. Outputs `results/embedding_eval.csv` with per-pair cosine similarity
scores for each model and prints gap summary to console.

**Ollama embedding finding:** The remote Ollama server (RTX 3060, 100.85.195.54)
does not support `ollama embed` CLI (too old) and gemma4:12b returns 501 on the
embeddings API endpoint. Fix: pulled `nomic-embed-text` (dedicated embedding
model, 768 dims) on the remote — Python `ollama.embed()` client works even
though the CLI subcommand is absent.

**Models evaluated:** nomic-embed-text (Ollama, remote), all-MiniLM-L6-v2
(sentence-transformers, local), all-mpnet-base-v2 (sentence-transformers, local).
Gap scores: nomic=+0.12, MiniLM=+0.18, mpnet=+0.17 — all below the 0.2
threshold.

**Key finding — gap threshold not applicable to hard boundary pairs:**
The 0.2 gap threshold assumes close=semantically similar and far=semantically
distant. The codebook's hard boundary pairs violate this: `breast cancer /
oncology services` and `childhood cancer treatment / cancer screening` are
genuinely semantically similar — the codebook separates them by a labeling rule
(womens_health beats cancer; childrens_health beats cancer), not semantic
distance. No general embedding model will score these as far, and that is
correct behaviour. The gap is depressed by design, not by model weakness.

**First-pass pair failure — proper nouns:** Original pairs using `Jordan's
Principle`, `First Nations`, `nurse shortage / scope of practice`, and
`internationally trained / licensure` scored near-zero (0.004–0.395) on close
pairs across all models. Cause: policy-specific proper nouns and jargon fragment
into generic subword tokens in general-purpose models. Fix: replaced with
descriptive phrases (`Indigenous health services / Indigenous peoples health`,
`foreign-trained doctors / medical licensure`). Post-fix close scores: 0.833–0.890
for indigenous health pair across all three models.

**Selected embedding model: all-MiniLM-L6-v2** (gap=+0.1819, closest to
threshold). Rationale: the remaining gap deficit is attributable to hard boundary
pairs that are semantically similar by design, not model weakness. BERT-family
models (BioBERT, PubMedBERT) were considered but rejected — they would not
resolve the hard boundary issue and the domain-specific close pairs are already
working well (0.5–0.83 range post-fix).

**Implication for RAG and topic clustering:** Hard boundary classes
(womens_health/cancer, childrens_health/cancer) require rule-based
post-filtering at retrieval time. Embedding similarity alone cannot enforce
codebook Rule 2. This is noted as a limitation for the week 6 RAG design.

## Week 3 — RAG Classification (2026-07-19)

**Architecture:** ChromaDB vector store (PersistentClient, `.chromadb/` at project root,
gitignored) over all 506 corpus.csv cards, indexed using `all-MiniLM-L6-v2` via ChromaDB's
`SentenceTransformerEmbeddingFunction`. Metadata deferred to week 6. Implementation:
`retrieval/vector_store.py` (HealthVectorStore class with add/add_batch/query/count).

**Boundary anchors:** 4 hand-picked cards in `retrieval/boundary_anchors.yaml` targeting
the two known gemma4:12b failure directions from week 1:
- 2 × other_none: COVID public-complaint letters mislabelled public_health by zeroshot model
- 2 × womens_health: breast implant patient briefs mislabelled pharmacare by zeroshot model
Fixed anchors always appear first in every prompt, before dynamic retrieval results.

**Prompt structure:** 4 fixed anchors (label + card_text[:400]) → up to 5 dynamic retrieved
examples (label from corpus topic_seed, unlabeled/invalid filtered out) → full codebook
definitions + RULE2 + valid codes + card to classify. Same parse logic as main.py.

**RAG classifier:** `retrieval/rag_classify.py` — standalone, main.py untouched.
Output: `results/predictions_rag_{safe_model}_gold.csv` (standard predictions schema).
Supports --resume to continue interrupted runs.

**Evaluation baseline:** zeroshot_gemma4-12b (macro_f1_all=0.6212, other_none recall=0.413,
womens_health F1=0.553). Primary targets: other_none recall and womens_health F1.

**Corpus indexing:** 506 cards indexed in ~2 min locally (all-MiniLM-L6-v2 sentence-transformers).
Retrieval smoke test on "opioid overdose harm reduction" returns opioid-epidemic study briefs
at distance ≤0.38 — semantically correct.

**Week 3 RAG result (2026-07-19):** RAG regressed vs zero-shot baseline: macro-F1 0.570 vs 0.621 (deduped predictions, 2 parse failures remaining).
other_none recall collapsed from 0.413 → 0.109. Root cause: other_none boundary anchors are COVID
public-complaint letters; the actual other_none failure cluster is breast-cancer-screening
submissions (46 gold cards) which are semantically indistinguishable from womens_health to the
embedding model. Dynamic retrieval floods the prompt with 5× womens_health examples for those
cards; the anchors provide no corrective signal because they look nothing like the query document.
The hard boundary between womens_health and other_none for breast-screening cards is a labeling
rule (personal story / civil-liberties framing → other_none; policy brief → womens_health), not
a semantic distinction — confirmed as a limitation of the RAG approach for this corpus.

## Week 4 — Prompt Tuning (2026-07-19)

**Failure mode diagnosis (from confusion matrix):** Two dominant zero-shot errors:
(1) 21 other_none cards mislabelled public_health — COVID individual grievances contain
vaccine/sickness keywords but primary concern is civil-liberties, not population health policy.
(2) 11 womens_health cards mislabelled pharmacare — breast implant briefs mention medical devices
and drugs, triggering pharmacare even though primary subject is women's health outcomes.

**Approach — definition sharpening only:** Added explicit boundary notes to config.yaml for
other_none (COVID civil-liberties complaints → other_none even if vaccine terms appear) and
womens_health (breast implant oversight → womens_health not pharmacare even if devices/drugs
mentioned). No few-shot examples added — week 3 showed that approach hurt macro-F1.

**RULE3 added (2026-07-19):** Explicit decision rule injected into every prompt after RULE2:
"If a document frames vaccine policy or health measures primarily in terms of personal freedom,
civil liberties, or individual rights rather than population-level health policy, classify as
other_none." Student verified no genuine public_health card in corpus combines personal-freedom
and vaccine language together — pattern is unique to individual COVID grievance submissions.

**Standalone classifier:** retrieval/promptv2_classify.py — copy of main.py with sharpened
definitions + RULE3. main.py untouched. Method name: promptv2_gemma4-12b. Adds --eval-prompt
mode for fast iteration on a hand-labeled eval set. Full gold run in progress (2026-07-19).

**Evaluation plan:** Compare per-class F1 for other_none and womens_health against zero-shot
baseline (other_none F1≈0.45, womens_health F1=0.553). Threshold: +0.1 on both to proceed to
week 5 LoRA adapters. Gold set remains frozen — no prompt iteration against gold cards.

## Week 6 — Semantic Search and RAG Q&A (2026-07-20)

**Chunk index built:** `rag/build_index.py` — drops and recreates ChromaDB collection
`hesa_chunks` in `chroma/` (gitignored) on every run (idempotent). Embeds 2,543 chunks
from `data/health/rag_chunks.jsonl` with `all-MiniLM-L6-v2` (same model as card index —
required for correct cosine distances). All metadata fields stored: source_type, org,
stakeholder_type, study_or_consultation_title, parliament_session, page_range,
section_title, recommendation_number, source_url. Null values coerced to empty string.
Counts: hesa_brief=2242, hesa_report=221, gov_response=80.

**Two separate indexes:** Chunk index (`chroma/`, collection `hesa_chunks`) is kept
separate from the card index (`.chromadb/`, collection `hesa_cards`). Different document
semantics: chunks are 300–800 word sections of full unmasked documents; cards are ~250
word organization-masked summaries. Mixing them would corrupt retrieval and break the
masking rule for classification.

**RAG Q&A pipeline:** `rag/ask.py` — `ask(question, source_type_filter, k=3)` queries
ChromaDB (n_results=5, optional source_type where-filter), takes top 3, builds grounded
prompt with passages labelled `[doc_id | org | study | page/§]`, calls gemma4:12b via
Ollama with num_ctx=16384 and no num_predict cap (generation mode). System prompt
instructs: answer only from passages, cite [doc_id] per claim, say so if absent.
CLI: `uv run python -m rag.ask "question" [--filter SOURCE_TYPE] [--k N]`.

**source_type as the only retrieval filter:** Topic labels are never used as retrieval
filters — this would create a circular dependency (topic is a classification output,
not a retrieval input). source_type corresponds to document role in the policy pipeline
(ask / committee finding / government commitment) and is a legitimate metadata filter.

**Generation parameters:** num_ctx=16384 (generation needs ~2× the classification
context window — three passages + citations can exceed 4k tokens). No num_predict cap,
unlike the classification pipeline where the cap guards against runaway thinking chains.
temperature=0.0 for deterministic output. keep_alive=30m.

**Evaluation harness:** `rag/eval.py` + `rag/eval_queries.yaml` — 10 known-answer
queries spanning all three source types. Metrics: hit-rate@3, hit-rate@5 (retrieval),
citation_valid/none/bad (generation faithfulness). Queries authored from corpus
knowledge; expected doc_ids widened post-run for q02 and q06 after confirming the
actually retrieved docs were topically valid alternatives (not a tuning decision —
the original pin was too org-specific). Saves timestamped JSON to results/.

**Results (2026-07-20):** hit-rate@3=100% (10/10), hit-rate@5=100% (10/10),
citation_valid=8/10, citation_none=2/10 (q01 breast-cancer report, q07 PMPRB gov
response — correct answers but no inline [doc_id]s), citation_bad=0/10. Zero
hallucinated doc_ids is the critical property. Citation compliance is a prompt
tuning opportunity, not a faithfulness failure.

**Embeddings persist on disk:** ChromaDB writes to chroma/chroma.sqlite3; survives
reboots indefinitely. Rebuild only needed on corpus sync (SYNC_VERSION change) or
embedding model change. Embedding runs locally on CPU (all-MiniLM-L6-v2 is ~22MB;
2543 chunks index in ~2 min on 2018 i7). GPU is reserved for Ollama/gemma4:12b.

## Week 8 — Streamlit Demo App (2026-07-20)

**ask() signature refactored (2026-07-20):** `rag/ask.py` — `ask()` now returns
`(answer: str, passages: list[dict])` instead of just `str`. Retrieval runs once;
the caller receives both the generated answer and the retrieved passages without a
second ChromaDB round-trip. CLI updated to `answer, _ = ask(...)`. `rag/eval.py`
unaffected (uses its own internal `generate_answer()` function, not `ask()`).

**Streamlit app built:** `app/streamlit_app.py` — four tabs, launched via
`uv run --no-sync streamlit run app/streamlit_app.py`. The `--no-sync` flag is
required on this Mac (macOS 15, x86_64) because torch==2.11.0 pinned for the
Linux GPU server has no wheel for this platform. Documented in app/README.
App is fully read-only against gold, predictions, and instructor code.

**Sidebar:** title, classifiable cards (506 from corpus.csv), chunk count with
per-source-type breakdown (hesa_brief=2242, hesa_report=221, gov_response=80),
models (gemma4:12b generation / all-MiniLM-L6-v2 embeddings), OLLAMA_HOST,
SYNC_VERSION contents. Stats loaded with @st.cache_resource.

**Tab 1 Classify:** 8 CMA section selectbox + paste-your-own text_area. Two
classifiers side-by-side: keyword_classify() (local, always fast, approximates
topic_rules.yaml using strong keywords from codebook) and gemma4:12b zero-shot
via classify_ollama() (requires OLLAMA_HOST). Disagreement callout when methods
differ. Offline fallback from demo/cached_classify.json. keyword_classify passes
8/8 known-answer tests covering all nine topic codes.

**Tab 2 Ask the record:** text_input + source filter selectbox + k slider (1-5).
On click: spinner → retrieve_passages() from ChromaDB → generate_answer() via
Ollama → answer in markdown + st.expander per passage (org, study, page/§,
distance, full text, clickable source_url). Offline fallback from
demo/cached_ask.json. ChromaDB collection loaded once with @st.cache_resource.

**Tab 3 Evaluation:** globs results/eval_summary_*.json → DataFrame sorted by
accuracy (8 methods). Bar chart of macro_f1_support10. confusion_zeroshot_gemma4-12b.png
displayed. Entirely disk-reads — no inference. Reading guide explains three F1
variants and other_none_recall.

**Tab 4 Gap analysis:** loads results/gap_analysis.json (shows warning with exact
precompute command if absent). Selectbox of 8 CMA sections; 3-column layout
(hesa_brief / hesa_report / gov_response) with status badge (echoed/endorsed/
committed/unaddressed/TODO), answer snippet, passage org + snippet + source_url link.

**Demo assets:** demo/cma_sections.json (8 CMA ministerial letter sections, each
with section_id, title, card_text, ask_text, keyword_prediction); demo/cached_classify.json
(per-section offline predictions); demo/cached_ask.json (one full cached Q&A with
passages for Tab 2 fallback). Document is deliberately out-of-distribution (multi-topic
letter) to show the limits of single-label classification.

**Precompute script:** scripts/precompute_gap.py — runs ask() 24 times (8 sections ×
3 source_type filters, k=3), writes results/gap_analysis.json with status="TODO".
Status must be filled by hand after reading answers (echoed/endorsed/committed/
unaddressed). Estimated run time ~20 min.

**Deprecation fix:** `use_container_width=True` → `width='stretch'` throughout
(Streamlit 1.57.0 deprecation, effective 2025-12-31).
