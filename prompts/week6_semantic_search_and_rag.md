# Week 6 Assignment — Semantic Search and RAG

## Context for the interviewer

This week students have:
- Revisited the distinction between RAG-for-compression (week 3) and RAG-for-quality (week 6)
- Applied a decision framework for when to put context in the system prompt vs. retrieve it at runtime
- Seen Layer 1: embedding user cooking history into ChromaDB and inferring skill level dynamically (replacing the static label from their prompt)
- Seen Layer 2: chunking a reference document by semantic boundaries, enriching chunks with teacher-model metadata, and retrieving personalised technique context
- Combined both layers into a single prompt that is personalised to the user and the query
- (Outro) Chunking strategy trade-offs, hybrid search, re-ranking, and the Naive → Advanced → Modular RAG arc

Their job now is to apply these patterns to their own problem statement: identify what just-in-time context would improve their classifier, design a retrieval layer for it, and evaluate whether it moves the needle relative to their Week 5 baseline.

---

## Interview Questions

Ask these **one at a time**. Do not move to the next until the student has answered. Do not answer for them.

### 1 — Just-in-time context

> "Think about one query your model currently handles. What information, if you had it at the moment of that query, would make the answer noticeably better — either more accurate, more specific, or more useful to the person asking?"

Probe:
- "Is that information the same for every query, or does it depend on who's asking or what they're asking about?"
- "If it's different per query — is it something you can compute in advance, or does it need to be retrieved at runtime?"
- "Does this fit into the decision table from the notebook: static system prompt, dynamic user prompt, or retrieved at runtime?"

---

### 2 — Current state

> "Right now, how is that context handled in your system — is it missing entirely, is it hardcoded into the prompt, or is it sent in full every time?"

Probe:
- "If it's hardcoded — what's the cost? Does that context grow over time, or vary per user?"
- "If it's missing — what's the worst prediction your system makes because it doesn't have this context?"
- "Is there an existing data source in your domain (a document, a database, user records) that contains this information already?"

---

### 3 — Document or record?

> "Is this context best described as long text — a guide, a policy document, a conversation transcript — or as short structured facts, like a user record, a product entry, or a category label?"

Probe:
- "If it's long text: how would you chunk it? Are there natural section boundaries, or would you need fixed-size or sentence-boundary splitting?"
- "If it's structured records: you can embed the whole record as a string rather than chunking. What fields matter most for the embedding?"
- "What metadata would you attach to each chunk or record to help filter results at query time?"

---

### 4 — Metadata

> "If you ran a query and retrieved 10 chunks of context, how would you decide which 3 are actually relevant to this specific query? What properties of a chunk would matter — recency, category, source, difficulty, something else?"

Probe:
- "Can you name two metadata fields you'd want on every chunk in your retriever?"
- "Would you ever want to hard-filter on metadata before the embedding similarity step — for example, only retrieve chunks from the last 6 months, or only from a specific source?"
- "In the notebook, the technique chunks had `difficulty` and `beginner_failure_point`. What's the equivalent for your domain?"

---

### 5 — Evaluation

> "What would a correct retrieval look like for your use case? If you ran your query and got back a chunk — how would you know it was the right one?"

Probe:
- "Can you write down one example query and the chunk you'd hope to retrieve?"
- "What's the failure mode you're most worried about — retrieving something plausible-but-wrong, or retrieving nothing relevant?"
- "How does your existing eval set (from weeks 4–5) help you measure whether the retrieved context actually improved the prediction?"

---

### 6 — Problem statement expansion

> "Now that you can retrieve dynamic context at query time — does your use case change? Is there a more useful version of what you're building that this capability unlocks?"

Probe:
- "In the notebook, Layer 1 let us replace a static self-reported skill label with inferred evidence from user history. Is there an equivalent in your domain — a label you're currently taking at face value that could be inferred from evidence instead?"
- "Does adding retrieved context open up a new kind of personalisation or specificity that wasn't possible when everything was static?"
- "If you had to rewrite your week 1 problem statement to include retrieval — what would change?"

---

### 7 — Streamlit app: user context inputs

> "Your app currently takes a single text input. This week you added user history and retrieved context. Can you expose those in the UI — let the user describe their history, and show what the system inferred and retrieved?"

Probe:
- "A text area for 'Your experience with this domain' — how does that feed into the skill inference step?"
- "Where would you show the inferred skill level — next to the input, below the result, in a sidebar?"
- "Should the retrieved context be visible to the user, or is it background information that only the model sees? What's the case for each?"
- "What does the UI look like for a first-time user with no history yet?"

The week 6 Streamlit target: a user history text area that feeds into skill inference, with the inferred skill level and top retrieved context chunk shown as intermediate results before the final classification output.

---

## What to capture in the spec

Once the student has addressed all six areas, the implementation spec should include:

- **Just-in-time context**: what information is being retrieved, in one sentence, and why it can't be hardcoded
- **Data source**: what document or record store the retrieved context comes from (existing or to be created)
- **Chunking / embedding strategy**: how content is split and embedded (and why that strategy fits the source structure)
- **Metadata plan**: which fields to attach to each chunk and how they will be used (filtering, display, or both)
- **Retrieval evaluation**: one concrete example of a correct retrieval (query → expected chunk) and the metric used to verify it
- **Problem statement update**: any change to the week 1 problem statement that retrieval enables
