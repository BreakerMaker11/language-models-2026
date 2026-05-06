# Image Generation Prompts — Week 3 Diagrams

Use these prompts with any image generation tool (DALL-E, Midjourney, Stable Diffusion, etc.).
Save the outputs to the paths listed below.

---

## 1. attention-mechanism-flow.png

**Target path:** `notebooks/resources/week3/attention-mechanism-flow.png`
**Style:** White background, flat design, no shadows, clean sans-serif font, 1200×700px

**Prompt:**
```
A clean educational diagram on a white background showing how the attention mechanism
transforms tokens into context-aware representations. Five horizontal rows, each connected
by downward arrows, laid out top to bottom:

Row 1 — four rounded token boxes side by side:
  [chicken]  [marinated]  [overnight]  [yogurt]
  Each box has a distinct pastel fill (light orange, light blue, light green, light purple).

Row 2 (below, connected by four downward arrows):
  Label centred across the row: "embed each token into a vector"
  Below the label: four small vertical bar icons representing embedding vectors,
  one under each token box.

Row 3 (below, connected by four downward arrows):
  Label: "compute pairwise dot-product scores (4×4 matrix)"
  A 4×4 grid of small circles in a light grey box; cells shaded from white to
  dark blue to suggest varying similarity scores. Row and column headers repeat
  the four token names in tiny text.

Row 4 (below, connected by one wide downward arrow):
  Label: "softmax each row → attention weights"
  The same 4×4 grid but now each row sums to 1 (annotated with a small "Σ = 1"
  callout on the right). One cell per row highlighted in orange to indicate the
  strongest weight.

Row 5 (below, connected by one wide downward arrow):
  Label: "weighted sum of value vectors → new representation for each token"
  Four output vector bars, wider than the input bars, each labelled "context-aware
  embedding". A small curved annotation arrow from the [overnight] column in the
  attention matrix points toward the [marinated] output bar, labelled
  "overnight enriches marinated".

Caption at the bottom:
"Each token pools meaning from every other token — weighted by relevance"

Clean, minimal, professional infographic style, no shadows, flat design. 1200×700px.
```

---

## 2. qkv-self-attention.png

**Target path:** `notebooks/resources/week3/qkv-self-attention.png`
**Style:** White background, flat design, three-column layout, clean sans-serif font, 1200×600px

**Prompt:**
```
A clean educational diagram on a white background explaining the Query, Key, Value (Q, K, V)
projections in self-attention. Three equal-width columns separated by thin vertical dividers,
each column a different pastel shade (light blue for Q, light green for K, light orange for V):

Column 1 — Query (Q)  (light blue background)
  Large bold label at top: "Q — Query"
  Subtitle: "What am I looking for?"
  Icon: a magnifying glass outline
  Example box below icon:
    Token: "marinated"
    Thought bubble: "What adds flavour or time context near me?"

Column 2 — Key (K)  (light green background)
  Large bold label at top: "K — Key"
  Subtitle: "What do I advertise?"
  Icon: a key outline
  Example box below icon:
    Token: "overnight"
    Thought bubble: "I signal duration and preparation intensity"

Column 3 — Value (V)  (light orange background)
  Large bold label at top: "V — Value"
  Subtitle: "What do I contribute?"
  Icon: a gift-box / package outline
  Example box below icon:
    Token: "overnight"
    Thought bubble: "Here is my meaning — long marination"

Below all three columns, a single centred formula box with light grey background:
  Attention(Q, K, V) = softmax( QKᵀ / √d_k ) · V

Below the formula, a one-line caption:
"Q·Kᵀ measures relevance; V carries the content that gets blended in"

Flat design, no shadows, clean sans-serif font, professional infographic. 1200×600px.
```

---

## 3. causal-attention-mask.png

**Target path:** `notebooks/resources/week3/causal-attention-mask.png`
**Style:** White background, flat design, side-by-side comparison layout, clean sans-serif font, 1400×600px

**Prompt:**
```
A clean educational diagram on a white background contrasting bidirectional attention
(BERT-style) with causal / autoregressive attention (GPT / Gemma-style).

Two equal-sized panels side by side, separated by a thin vertical divider:

LEFT PANEL — "Bidirectional Attention (BERT)"
  Header badge in light blue: "BERT · encoder models · fill-in-the-blank"
  A 6×6 grid of small squares. Every square is filled with a medium blue colour,
  indicating every token attends to every other token.
  Row labels on the left (token positions 0–5): t₀ t₁ t₂ t₃ t₄ t₅
  Column labels on top (same): t₀ t₁ t₂ t₃ t₄ t₅
  Caption below: "Each token sees all positions — past and future"

RIGHT PANEL — "Causal Attention (GPT / Gemma)"
  Header badge in light orange: "GPT · Gemma · decoder models · generation"
  A 6×6 grid. Only the lower-left triangle (including diagonal) is filled in
  dark orange; the upper-right triangle is white with a light grey × pattern.
  Row labels: t₀ t₁ t₂ t₃ t₄ t₅
  Column labels: same
  A small annotation arrow pointing to the upper-right white area labelled
  "masked — future tokens unseen"
  Caption below: "Each token sees only itself and earlier positions"

Bottom centre, spanning both panels:
  "Gemma 2B uses causal masking — it generates left to right, one token at a time"

Flat design, no shadows, clean sans-serif font, professional infographic. 1400×600px.
```

---

## 4. transformer-depth.png

**Target path:** `notebooks/resources/week3/transformer-depth.png`
**Style:** White background, flat design, vertical stack with annotations, clean sans-serif font, 900×800px

**Prompt:**
```
A clean educational diagram on a white background showing that a transformer is a
stack of repeated attention layers, using Gemma 2B as the concrete example.

Central element: a tall vertical stack of 26 identical slim rectangular blocks,
each labelled "Attention Layer" with a small gear icon. The blocks are shaded from
light blue at the bottom to slightly darker blue at the top to suggest depth.
Between each pair of blocks, a short upward arrow.

Left side annotations (horizontal arrows pointing into the stack at key positions):
  → at layer 1 (bottom): "token embeddings enter here"
  → at layer 13 (middle): "intermediate representations — syntax, local meaning"
  → at layer 26 (top): "final representation — rich contextual meaning"

Right side: a small table with two rows and two columns:
  Model         | Layers
  GPT-2 small   |  12
  Gemma 2B      |  26  ← highlighted row in light orange

Below the stack, a complexity callout box with light grey background:
  "O(n²) attention: doubling the sequence length quadruples the computation"
  "Gemma 2B context limit: 8,192 tokens"

Caption at bottom:
"Every layer refines the representation — deeper layers capture longer-range meaning"

Flat design, no shadows, clean sans-serif font, professional infographic. 900×800px.
```

---

## 5. semantic-retrieval-pipeline.png

**Target path:** `notebooks/resources/week3/semantic-retrieval-pipeline.png`
**Style:** White background, flat design, left-to-right pipeline, clean sans-serif font, 1400×500px

**Prompt:**
```
A clean educational pipeline diagram on a white background showing how semantic
retrieval with a vector database extends an LLM's effective context.

Two horizontal rows, each a labelled pipeline phase:

TOP ROW — "Offline: Build the Index" (light blue background banner)
  Three boxes connected by right-pointing arrows:

  Box 1: "Labelled Recipes"
    Icon: stack of documents
    Body: "1,000 labelled examples\n(30 min, 1 hr, 2 hr, …)"

  → Arrow

  Box 2: "Embed with Gemma"
    Icon: small vector bar chart
    Body: "ollama.embeddings()\neach recipe → 2048-d vector"

  → Arrow

  Box 3: "Store in ChromaDB"
    Icon: cylinder database icon
    Body: "vector index on disk\nfast nearest-neighbour search"

BOTTOM ROW — "Online: Classify a New Recipe" (light orange background banner)
  Four boxes connected by right-pointing arrows:

  Box 1: "New Recipe"
    Icon: single document
    Body: "unlabelled input text"

  → Arrow

  Box 2: "Embed Query"
    Icon: magnifying glass over vector bars
    Body: "same embedding model\n→ 2048-d query vector"

  → Arrow

  Box 3: "Retrieve k=5 Nearest"
    Icon: database cylinder with highlighted rows
    Body: "cosine similarity search\nreturns 5 similar recipes + labels"

  → Arrow

  Box 4: "Few-shot Prompt"
    Icon: chat bubble with bullet list
    Body: "5 examples injected into\nGemma prompt → classify"

A vertical dashed divider between the two rows labelled "context window never overflows".

Caption at bottom:
"Retrieval lets you use all 1,000 examples without fitting them in the 8,192-token window"

Flat design, no shadows, clean sans-serif font, professional infographic. 1400×500px.
```

---

## 6. training-vs-inference.png

**Target path:** `notebooks/resources/week3/training-vs-inference.png`
**Style:** White background, flat design, two-panel side-by-side comparison, clean sans-serif font, 1400×700px

**Prompt:**
```
A clean educational diagram on a white background contrasting how a transformer
works during training versus during inference. Two equal-width panels side by side,
separated by a thin vertical divider.

LEFT PANEL — "Training" (light blue background banner at top)
  A vertical pipeline with four stages connected by downward arrows:

  Stage 1 — "Full sequence fed in at once"
    A row of five token boxes in pastel colours:
    [chicken] [marinated] [overnight] [yogurt] [→ ?]
    Label below: "all tokens known upfront"

  Stage 2 — "Causal mask applied"
    A small 5×5 lower-triangular grid (dark blue filled cells, white upper triangle)
    Label: "each position only sees past tokens — even though all are in memory"

  Stage 3 — "Loss computed at every position"
    Five small red Δ (delta) icons, one above each token, connected to a single
    "Cross-entropy loss" box. Label: "prediction vs ground truth"

  Stage 4 — "Weights updated via backpropagation"
    A horizontal bar representing model weights with a leftward orange arrow labelled
    "gradients flow backward → Q, K, V matrices updated"

  Bottom badge: light blue pill labelled "Parallel — one forward pass processes the whole sequence"

RIGHT PANEL — "Inference" (light orange background banner at top)
  A loop diagram showing autoregressive generation across three steps:

  Step 1:
    Input box: [chicken] [marinated] [overnight] [yogurt]
    Downward arrow into a small transformer block icon
    Output token box (highlighted in orange): [needs]
    Label on right: "step 1 — generate first new token"

  Step 2 (below, connected by a curved arrow looping back to input):
    Input box: [chicken] [marinated] [overnight] [yogurt] [needs]
    Downward arrow into transformer block
    Output token: [long]
    Label: "step 2 — append and repeat"

  Step 3 (below, same pattern):
    Input box: [chicken] [marinated] [overnight] [yogurt] [needs] [long]
    Downward arrow into transformer block
    Output token: [time]
    Label: "step 3 — stop when done"

  A small "KV Cache" cylinder icon on the right of the transformer blocks with a
  dashed arrow labelled "past keys/values cached — no recomputation"

  A small crossed-out gradient icon labelled "no weight updates — frozen model"

  Bottom badge: light orange pill labelled "Sequential — one token generated per forward pass"

Caption at bottom centre spanning both panels:
"Same architecture, same weights — training updates them, inference uses them"

Flat design, no shadows, clean sans-serif font, professional infographic. 1400×700px.
```
