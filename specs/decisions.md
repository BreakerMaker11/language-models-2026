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
