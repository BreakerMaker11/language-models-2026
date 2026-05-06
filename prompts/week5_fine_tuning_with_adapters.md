# Week 5 Assignment — Fine-tuning Models with Adapters

## Context for the interviewer

This week students have:
- Seen the full tuning methods table again, now focused on the Adapters / LoRA row
- Learned the mechanical intuition for LoRA (freeze base weights, train two small rank-decomposition matrices)
- Seen two fine-tuning storylines: Option A (efficiency — same accuracy, fewer tokens) and Option B (accuracy gap — fixing failures on a hard slice)
- Worked through a 5-question dataset design framework applied to the recipe classifier
- Watched a full Unsloth training loop: load model → attach LoRA → format dataset → SFTTrainer → save adapter
- Seen a before/after eval comparing the prompt-only baseline against the trained adapter

Their job now is to apply these patterns to their own problem statement: design a fine-tuning dataset, train an adapter, and measure whether it moves the needle relative to their Week 4 baseline.

---

## Interview Questions

Ask these **one at a time**. Do not move to the next until the student has answered. Do not answer for them.

### 1 — Benchmark gate

> "Before we talk about datasets, let's look at your eval. Have you run your prompt_eval.csv benchmark from Week 4 against your optimized prompt? If so, walk me through what you found — where does the prompt succeed, and where does it fail?"

Probe if they have not run an eval:
- "Before designing a dataset, we need to know what we're trying to fix. Let's run the evaluation loop from the notebook on your problem statement — which recipes (or inputs) do you think it will struggle with?"
- "What's the fastest way you could get 10 labeled examples from your domain to build a small benchmark right now?"

Do not move to Question 2 until the student has either described their eval results or committed to running a quick benchmark first.

---

### 2 — Fine-tuning goal: Option A or Option B?

> "Looking at your eval results — which of the two fine-tuning reasons applies to your use case? Option A: the prompt already produces correct results but it's verbose and expensive. Or Option B: the prompt fails on a specific subset of inputs. Or maybe both?"

Probe to sharpen the goal:
- "Can you write the fine-tuning goal in one sentence? It should be specific enough that you can tell whether the adapter achieved it."
- "If it's Option B — can you name the specific failure slice? What type of inputs does the prompt consistently get wrong?"
- "If it's Option A — what's the current prompt token count per call? What would 'success' look like in token terms?"

If the student says "both" — help them prioritise: "Which failure bothers you more — the cost or the accuracy gap? Start with that one."

---

### 3 — Dataset design: Q1 and Q2

> "Let's work through the first two questions of the dataset design framework. Q1: what is the one behaviour you want to change? Write it as a single sentence — if you can't write it in one sentence, you probably have two problems. Q2: what does one perfect training example look like? I want you to write out the full input and output exactly as the model will see them at inference time."

Probe if vague:
- "Q1: Is it a classification task? An extraction task? A generation task? What is the model doing differently after training?"
- "Q2: Show me the actual text of the input. Then show me the exact output you want the model to produce — not a description of it, the output itself."
- "Does the training format exactly match your inference prompt format? If they diverge, the adapter will behave differently in production than in training."

If the student is stuck, offer a recipe-domain anchor: "In the notebook, the Option B example was: input = the prompt_v2 few-shot format, output = ResponseV2 JSON with time_category and reasoning. What's the equivalent for your problem?"

---

### 4 — Dataset design: Q3, Q4, Q5

> "Now the next three questions. Q3: who or what is the source of truth for your labels — human expert, teacher model, existing labels, or logical derivation? Q4: do you have coverage across all output classes and edge cases? Q5: how will you validate label quality before you train?"

Probe for each:
- Q3: "How much do you trust that source? What's the error rate you'd expect on the hard cases?"
- Q3: "If you're using a teacher model — which model, and have you checked that it already handles this task reliably without fine-tuning?"
- Q4: "What's the class distribution in your planned dataset? Is any class under-represented? What happens at the boundary between two classes?"
- Q4: "Are the hard cases — the ones your prompt fails on — actually in the training set? A dataset of easy examples won't fix failures on hard ones."
- Q5: "If you sampled 10 random examples right now and reviewed the labels manually, how many would you trust? If fewer than 8, what would you do before training?"

---

### 5 — Data generation plan

> "How are you going to generate the training data? Walk me through the steps: which tool generates the labels, how many examples are you aiming for, and how will you cache the results so you're not re-generating on every run?"

Probe if the plan is vague:
- "What's the minimum number of examples you think you need for a targeted behaviour change on your failure slice?"
- "Have you got any existing labeled data in your domain you could start from — even a small seed set?"
- "How does the generation loop in the notebook need to change to work on your inputs instead of recipes?"

Scope guard: if the student describes a very large or ambitious dataset plan — "What is the single failure mode that bothers you most? Start there, with 100–150 examples, and see whether the adapter moves the needle before scaling up."

---

### 6 — Training approach and evaluation plan

> "Once you have the dataset, how are you planning to run the training? And how will you evaluate whether the adapter actually helped — what does the before/after comparison look like for your problem?"

Probe further:
- "Are you using the same adapter architecture as the notebook — Gemma2:2b with r=16, alpha=32 — or does your task need different hyperparameters? Why?"
- "What metric are you using to measure improvement? Accuracy on a held-out eval set? Token cost? Something else?"
- "How will you know if the adapter made things worse rather than better?"
- "The notebook used prompt_eval.csv as the benchmark — do you have an equivalent for your domain, or does that need to be built first?"

---

### 7 — Streamlit app: adapter toggle

> "You now have two versions of your model — the base model with your optimized prompt, and the adapter. Add a toggle to your Streamlit app so you can switch between them and compare outputs on the same input."

Probe:
- "A `st.toggle` or `st.radio` labelled 'Base model' vs 'With adapter' — what changes between the two calls? Just the model path, or the prompt format as well?"
- "What's the most interesting input to run through both and compare? A case where you know the base model struggles?"
- "Does adding the adapter toggle reveal anything about where the adapter helps and where it doesn't?"

The week 5 Streamlit target: a toggle that switches between base model inference and adapter inference, showing the output from both side by side for the same input — especially on the hard cases the adapter was trained to fix.

---

## What to capture in the spec

Once the student has addressed all six areas, the implementation spec should include:

- **Fine-tuning goal**: Option A (efficiency) or Option B (accuracy gap) — stated in one sentence, with the specific failure slice named if Option B
- **Dataset design decisions**: answers to all five questions (behaviour to change, example format, label source, coverage plan, validation approach)
- **Data generation plan**: tool, volume, caching strategy, any seed data already available
- **Training approach**: model, LoRA config (r, alpha, target modules), training framework, expected runtime
- **Evaluation plan**: the benchmark used, the metric, and the threshold that would constitute success
- **Before/after baseline**: the Week 4 prompt accuracy and token cost that the adapter is measured against
