# Image Generation Prompts — Week 1 Diagrams

Use these prompts with any image generation tool (DALL-E, Midjourney, Stable Diffusion, etc.).
Save the outputs to the paths listed below.

---

## 1. next-token-prediction.png

**Target path:** `notebooks/resources/week1/next-token-prediction.png`
**Style:** White background, flat design, no shadows, clean sans-serif font, 1200×700px

**Prompt:**
```
A clean educational diagram on a white background showing how LLMs generate text one token at a time.

Main area: a row of four word boxes in sequence — "Imagine", "you", "have", "a" — connected with
a right-pointing arrow. To the right of them, a dashed empty box labelled "?". Below the "?" box:
a vertical bar chart showing five candidate next tokens and their logprob values:
  "A: -0.12 (chosen)"  — very tall bar, highlighted in orange
  "The: -2.5"          — shorter bar
  "In: -3.1"           — shorter bar
  "It: -3.8"           — shorter bar
  "So: -4.2"           — very short bar
The "A" bar is highlighted in orange. A curved arrow goes from the top of the "A" bar up into the
"?" box, which then shows "A" filled in and highlighted in orange.

Top-right inset panel: a light grey code block with the label "code that produces this" showing:
  result = ollama.generate(
      model="gemma2:2b",
      prompt="What is a logprob in LLMs? ELI5",
      top_logprobs=5,
      logprobs=True
  )

Below the code block, a dashed output box showing the print_log_prob output format:
  ----------
  Chosen Token: ** A **
  Tokens Considered:
   A: -0.12 || The: -2.5 || In: -3.1 || It: -3.8 || So: -4.2

Caption below the main diagram:
"result.logprobs — every token position records what the model considered"

Clean, minimal, professional infographic style, no shadows, flat design. 1200×700px.
```

---

## 2. llm-application-stack.png

**Target path:** `notebooks/resources/week1/llm-application-stack.png`
**Style:** White background, flat design, no gradients, clean sans-serif font, 1000×700px

**Prompt:**
```
A clean educational layered-stack diagram on a white background showing the difference between
an LLM and an LLM application. Three wide horizontal rectangles stacked vertically, each a
different shade of blue:

- Bottom rectangle (dark navy): bold label "gemma2:2b" with smaller text below
  "2B parameters · Google DeepMind"

- Middle rectangle (medium blue): bold label "import ollama" with a second line showing
  'ollama.generate(model="gemma2:2b", prompt="...")'
  and smaller text below: "runs on your laptop"

- Top rectangle (light teal/sky blue): bold label "your recipe classifier" with smaller text
  "ChatGPT · Claude Code · NotebookLM"

A vertical upward arrow on the left side spans all three layers, labelled "each layer calls the
one below".

Flat design, no gradients, clean sans-serif font, professional infographic style. 1000×700px.
```

---

## 3. training-phases.png

**Target path:** `notebooks/resources/week1/training-phases.png`
**Style:** White background, flat design, pastel colours, minimal line-art icons, clean sans-serif font, 1400×600px

**Prompt:**
```
A clean educational pipeline diagram on a white background showing the three training phases of a
modern LLM. Three rectangular boxes arranged left to right, connected by thick rightward arrows:

Box 1 — "Pre-training"
  Icon: large stack of documents
  Body: "Raw web text\n3 trillion tokens"
  Output label below box: "Base model — continues text"

Arrow →

Box 2 — "Instruction Fine-tuning"
  Icon: speech bubble / conversation icon
  Body: "Curated conversations\n& instructions"
  Output label below box: "Chat model — follows instructions"

Arrow →

Box 3 — "RLHF"
  Icon: thumbs up / human rating icon
  Body: "Human preference\nrankings"
  Output label below box: "Assistant — helpful & aligned"

On the right edge of the diagram, a "you are here" callout arrow pointing to the output of Box 3,
with a code label:
  ollama.generate(model="gemma2:2b", prompt="...")

Below all three boxes, a thin banner reads:
"The model you've been running — gemma2:2b — is the product of all three phases above.
 512 TPUs · 3 trillion tokens · ~131 tonnes CO₂ for pre-training alone"

Flat design, icons minimal and line-art style, each box a different pastel colour
(light blue, light green, light orange), white background, clean sans-serif font. 1400×600px.
```
