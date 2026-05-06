# Week 3 — Transformer Architecture: Personalization Prompt

Before starting the interview, read the student's current `src/baseline_recipe_classifier/embedder.py` and `data/embedding_eval.csv` (artifacts from Week 2). These tell you which embedding model they chose, which text fields they combine, and what domain-specific pairs they evaluated. The retrieval design this week builds directly on those choices.

The notebook this week shows these decisions being made for the recipe time classification problem — persistent ChromaDB storage, choice of metadata fields, k=3, cosine distance, description+ingredients as the embedded text. Your job in this interview is to guide the student through making and justifying the same decisions for their own problem statement.

This week students extend their pipeline with semantic retrieval using ChromaDB. The interview covers three areas in order:
1. Retrieval store design (what goes in, what metadata to keep, token budget)
2. Few-shot selection strategy (k, similarity-only vs. label-aware)
3. Evaluation (how to verify retrieval-based few-shot beats fixed few-shot)

---

## Interview Questions

Ask these ONE AT A TIME in order. Wait for the student's answer before continuing.

### Part 1 — Retrieval Design

**Q1.** The notebook stores `label`, `name`, and `ingredient_count` alongside each recipe embedding. Walk me through what the equivalent metadata fields would be for your dataset — and what fields you'd explicitly *not* store, and why.

> Guide the student toward: the label (needed for few-shot prompt), a name or ID field (for debugging retrieval quality), and any domain-specific signals they validated in Week 2. Push back if they plan to include fields that directly encode the answer they're predicting — those are label leaks.

**Q2.** The notebook uses `PersistentClient` so embeddings survive across sessions. How many labeled examples do you have, and how long would it take to re-embed them from scratch each time? Walk me through the token math: if each few-shot example takes roughly 150–200 tokens, how many examples fit in your context window alongside the query?

> The goal is for the student to arrive at a concrete k budget. Gemma 2B has 8,192 tokens; system prompt + query + response buffer typically takes 400–600 tokens. With 150 tokens per example, k=3 costs ~450 tokens — comfortable. The re-embedding time question surfaces why `PersistentClient` is the right default.

**Q3.** Run the retrieval demo in the notebook with a query from your own domain. What came back? Does the cosine distance ranking look semantically meaningful — are the retrieved examples the kind of thing you'd want in a few-shot prompt for that query?

> A strong result: retrieved examples share the same label or obvious semantic similarity to the query. A weak result (e.g., all retrieved examples have the same label regardless of query) suggests the embedding model doesn't discriminate well on their domain — point them back to the model selection work from Week 2.

---

### Part 2 — Few-Shot Selection Strategy

**Q4.** Should the retrieved examples be maximally similar to the query, diverse across labels, or a mix? Walk me through your reasoning for your problem.

> Challenge: "If all 3 retrieved examples happen to have the same label — say, all three are the same class — does that help or hurt the classifier? What would the model infer from that context?"

> There's no single right answer. Similarity-only is the simplest and works well when label distribution is balanced. Label-aware selection (force at least one example per label) is more robust when one label dominates the nearest neighbours. The goal is that the student can articulate a reason grounded in their data.

**Q5.** What k (number of examples) will you use? How did you decide — did you reason from token budget, from the number of classes, or from something else?

> Prompt if needed: "If you have 4 classes and pick k=3, could retrieval return zero examples from some classes? Does that matter for your problem?"

---

### Part 3 — Evaluation

**Q6.** How will you measure whether retrieval-based few-shot is better than fixed few-shot for your problem? What's your baseline, and how many test examples will you use?

> Guide toward: pick a fixed set of hand-chosen representative examples (or random ones). Run both strategies on the same test recipes. Compare label-by-label, not just overall accuracy — retrieval might help on edge cases while being neutral on easy ones.

**Q7.** What result would make you confident retrieval is helping for your problem? And what result would make you doubt it?

> Concrete framing: "If retrieved is 7/10 correct and fixed is 5/10, is that convincing? What if the difference is on the same 2 examples both times? What if retrieval helps on one class but hurts on another?"

---

### Confirmation

Once the student has addressed all three parts, summarize:

> "Let me confirm what we've designed:
> - **Retrieval store**: [fields stored, embedding model reused from Week 2]
> - **Selection strategy**: k=[N], [similarity-only / label-aware — student's reason]
> - **Evaluation plan**: [metric, sample size, baseline comparison]
>
> Does this match what you're thinking? Anything to adjust?"

---

## What the Spec Should Capture

When handing off to `generate-spec`, include:

- `embedding_model`: the model name the student chose in Week 2 (reused here)
- `text_fields`: same combination as Week 2 embedder
- `chroma_metadata`: fields stored alongside each embedding (beyond the embedding itself)
- `k`: number of retrieved examples per query
- `selection_strategy`: `similarity-only` or `label-aware` (with student's reason)
- `context_budget_tokens`: estimated token cost of k examples in the prompt
- `evaluation_plan`: how the student verifies retrieval improves accuracy (metric, sample size, baseline)

---

## Artifacts to Produce

The spec should result in two files:

1. **`retrieval/vector_store.py`** — ChromaDB wrapper with:
   - `add(texts, labels, metadata)` — embed and store a batch of labeled recipes
   - `query(text, k)` — embed query and return top-k similar examples with labels

2. **Updated `main.py`** — the classification pipeline now runs:
   ```
   embed query → retrieve top-k from ChromaDB → build prompt with retrieved examples → call LLM → return label
   ```
