# Image Generation Prompts — Week 2 Diagrams

Use these prompts with any image generation tool (DALL-E, Midjourney, Stable Diffusion, etc.).
Save the outputs to the paths listed below.

---

## 1. tokenization-pipeline.png

**Target path:** `notebooks/resources/week2/tokenization-pipeline.png`
**Style:** White background, flat design, no shadows, clean sans-serif font, 1400×500px

**Prompt:**
```
A clean educational pipeline diagram on a white background showing how text becomes vectors in an LLM.

Five rectangular boxes arranged left to right, connected by thick rightward arrows. Each box has a bold label at the top and example content below:

Box 1 — "Raw Text"
  Content: "sourdough bread recipe"  (shown in a light grey code block)

Arrow →

Box 2 — "Tokenizer (BPE)"
  Content: ["sour", "dough", "bread", "recipe"]  (each piece in its own small pill/chip shape)

Arrow →

Box 3 — "Token IDs"
  Content: [4521, 8830, 1204, 9301]  (numbers in a light blue code block)

Arrow →

Box 4 — "Embedding Layer"
  Content: a small 4×4 grid of numbers representing one high-dimensional vector, with an annotation "256,128 vocab entries → 2048-dim vectors"

Arrow →

Box 5 — "Transformer Layers"
  Content: stacked horizontal bars (abstract representation of transformer blocks) with a downward arrow labelled "next token prediction"

Boxes should alternate between light blue and light teal. Flat design, clean sans-serif font, professional infographic style. 1400×500px.
```

---

## 2. embedding-space.png

**Target path:** `notebooks/resources/week2/embedding-space.png`
**Style:** White background, flat design, soft colours, clean sans-serif font, 1000×800px

**Prompt:**
```
A clean educational 2D scatter plot on a white background showing how words cluster in embedding space.

The axes are unlabelled (representing reduced high-dimensional space). A subtitle at the top reads: "Embedding space — reduced to 2D for visualisation".

Three distinct clusters of labelled dots:

Cluster 1 (top-left, light orange dots): "bake", "roast", "grill", "broil" — circled with a dashed orange boundary, labelled "cooking methods"

Cluster 2 (bottom-right, light blue dots): "sourdough", "fermentation", "yeast", "leaven" — circled with a dashed blue boundary, labelled "fermentation concepts"

Cluster 3 (centre-left, light green dots): "julienne", "dice", "mince", "chop" — circled with a dashed green boundary, labelled "cutting techniques"

Two isolated dots far from all clusters (grey, no circle): "combustion engine" (top-right corner) and "stock market" (bottom-left corner)

Dotted lines connecting Cluster 1 and Cluster 2 with a label "large distance = low similarity". Dotted lines connecting the two dots within Cluster 1 with a label "short distance = high similarity".

Bottom caption: "High similarity = short distance.  Low similarity = long distance."

Flat design, minimal gridlines, clean sans-serif font. 1000×800px.
```

---

## 3. cosine-similarity.png

**Target path:** `notebooks/resources/week2/cosine-similarity.png`
**Style:** White background, flat design, clean sans-serif font, 1000×600px

**Prompt:**
```
A clean educational diagram on a white background showing cosine similarity as the angle between vectors.

Three side-by-side panels, each showing two 2D vectors drawn as arrows from the same origin point:

Panel 1 — "hot sauce" vs "hot day":
  Two arrows with a moderate angle between them (~45°). The angle arc is labelled "~45°". Below: "some similarity  ≈ 0.70"

Panel 2 — "sourdough" vs "fermentation":
  Two arrows nearly pointing in the same direction (~10° apart). The angle arc is labelled "~10°". Below: "high similarity  ≈ 0.95"

Panel 3 — "sourdough" vs "combustion engine":
  Two arrows nearly perpendicular (~85° apart). The angle arc is labelled "~85°". Below: "low similarity  ≈ 0.08"

Below all three panels, a centred formula block:
  cos(θ) = (A · B) / (|A| |B|)
  annotated as:  1.0 = identical direction   ·   0.0 = perpendicular   ·   −1.0 = opposite

Flat design, arrows in different colours per panel (e.g. blue and orange), clean sans-serif font. 1000×600px.
```

---

## 4. bpe-merges.png

**Target path:** `notebooks/resources/week2/bpe-merges.png`
**Style:** White background, flat design, monospace font for token content, clean sans-serif labels, 1200×500px

**Prompt:**
```
A clean educational step-by-step table diagram on a white background showing Byte Pair Encoding (BPE) building up vocabulary entries.

Main section — four rows, each labelled on the left:

Row 0  "Characters:"   →  s | o | u | r | d | o | u | g | h   (each character in its own small pill/chip)

Row 1  "Step 1 merges:"  →  so | ur | do | ug | h   (merged pairs shown in slightly wider pills, with a faint annotation "most frequent pairs in training data")

Row 2  "Step 2 merges:"  →  sour | doug | h   (merged again, pills wider)

Row 3  "Result:"         →  two branches shown with a split arrow:
   - Top branch: "sourdough" (one pill, green background) — labelled "if frequent in training data"
   - Bottom branch: "sour" | "dough" (two pills, amber background) — labelled "if less common"

Right sidebar (separated by a vertical line): a contrasting example for a rare culinary term:
   Label: "rare word: escabeche"
   Row 0: e | s | c | a | b | e | c | h | e
   Result: "esca" | "be" | "che"  — fragmented, red background, labelled "stays fragmented — rare in training data"

Bottom caption: "BPE encodes frequency from training data.  Common words → single tokens.  Rare words → many pieces."

Flat design, monospace font for token content, clean sans-serif for labels. 1200×500px.
```

---

## 5. mteb-leaderboard.png

**Target path:** `notebooks/resources/week2/mteb-leaderboard.png`
**Style:** White background, flat design, clean sans-serif font, mockup/screenshot style, 1200×700px

**Prompt:**
```
A clean educational mockup of the MTEB leaderboard table on a white background, with annotation callouts pointing to key UI elements.

The central element is a simplified table with columns: "Model", "Size", "Avg Score", "Classification", "STS", "Retrieval". Three sample rows:
  Row 1: "bge-large-en-v1.5"   |  335M  |  64.2  |  67.1  |  86.5  |  54.3
  Row 2: "nomic-embed-text"    |  274M  |  62.4  |  65.3  |  83.1  |  52.0   ← this row circled in orange
  Row 3: "mxbai-embed-large"   |  670M  |  63.8  |  66.7  |  85.2  |  53.4

Above the table, a filter bar with dropdown chips labelled "Task: All ▾", "Language: English ▾", "Model size: All ▾". The "Task" dropdown is highlighted with a red dashed box.

Four annotation callout arrows pointing to:
1. The task filter dropdown → "Filter by your task type: Classification, STS, Retrieval"
2. The "Size" column header → "Check this if you need to run locally"
3. The "nomic-embed-text" row (circled in orange) → "The model we just used"
4. The "Avg Score" column header → "Higher is better — but filter by your task first"

Bottom caption: "huggingface.co/spaces/mteb/leaderboard"

Flat design, table with alternating light grey rows, clean sans-serif font, annotation arrows in red/orange. 1200×700px.
```
