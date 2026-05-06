# Week 7 Assignment — Multimodal Models

## Context for the interviewer

This week students have:
- Learned how multimodal models encode images as patch token sequences and fuse them with text using early fusion (interleaved tokens)
- Seen the full week 1–6 pipeline run end-to-end on a recipe photo: image → Gemma 4 extraction → classifier → skill inference (week 6 RAG) → technique context (week 6 RAG) → personalised response
- Understood the ViT → CLIP → LLaVA → Gemma 4 architecture progression and how Gemma 4's SigLIP encoder works
- Seen how audio (Whisper/spectrograms) maps onto the same architecture pattern

Their job now is to identify one visual input that their existing pipeline could consume — and add the vision layer that connects it. Nothing from weeks 1–6 should need to change. The vision step produces text; the text pipeline consumes it.

---

## Interview Questions

Ask these **one at a time**. Do not move to the next until the student has answered. Do not answer for them.

### 1 — What visual input exists in your domain?

> "Think about your problem statement. What does a user in your domain actually have in front of them? Is there a document, a photo, a screenshot, or a form that currently has to be typed out before your system can process it?"

Probe:
- "Would this input be the same every time, or does it change per user?"
- "Is the visual content structured (a form, a table, a recipe card) or unstructured (a photo of a scene)?"
- "If someone could point their phone at something in your domain and have your system respond — what would they point it at?"

---

### 2 — What needs to be extracted?

> "What specific information does your pipeline need from that image? Walk me through: what goes in as a photo, and what structured text comes out on the other side?"

Probe:
- "Write out the fields you'd want extracted — just the names. Recipe name, ingredients, directions. What's the equivalent for your domain?"
- "Is any of that information already available as text elsewhere, or is the image the only source?"
- "What does one perfect extraction look like? Write the input prompt and the expected JSON output exactly as the model will see them."

---

### 3 — Does extraction connect to your existing pipeline?

> "Once you have the extracted text — how does it feed into what you already built? Walk me from the extracted fields to the point where your week 5 classifier or week 6 retriever picks up."

Probe:
- "Does any of the extracted information map directly to an existing input field in your pipeline — like how the recipe name mapped to the classifier in the notebook?"
- "Is there any transformation needed between the extraction output and the pipeline input, or is it a direct pass-through?"
- "Which parts of your pipeline are unchanged by adding the visual input?"

---

### 4 — How will you evaluate extraction quality?

> "Before you connect the vision step to the rest of your pipeline — how will you know the extraction is good enough to trust? What does a correct extraction look like for your use case?"

Probe:
- "Write one example: here's an image I'd test on, and here's exactly what I expect the model to return."
- "What's the failure mode you're most worried about — the model missing a field, hallucinating information that isn't in the image, or returning the wrong format?"
- "How does your existing eval set (weeks 4–5) help you measure whether the vision-augmented pipeline is better or worse than the text-only baseline?"

---

### 5 — Does the visual input change your problem statement?

> "Now that your system can accept a photo — is there a more useful version of what you're building? Does removing the text-entry step change who can use it, or what they can use it for?"

Probe:
- "In the notebook, adding a recipe photo meant users didn't have to type the dish name — but the core task (time classification) stayed the same. What changes in your domain?"
- "Does the visual input reveal information the user couldn't or wouldn't have typed? Something that only shows up in the image?"
- "If you rewrote your week 1 problem statement to include a photo input — what would the new version say?"

---

### 6 — Full pipeline integration

> "Put it all together. Walk me through your updated pipeline from start to finish: what the user provides, what each stage does, and what they get back."

Probe:
- "Where in the pipeline does the vision step sit? Is it always the entry point, or is it optional depending on what the user provides?"
- "Does the rest of the pipeline — your adapter, your retriever, your prompt — need any changes, or does the vision step slot in cleanly at the front?"
- "What would the `classify_from_image` equivalent function look like for your domain? Name it and describe its signature."

---

### 7 — Streamlit app: image upload tab

> "Your app has grown from a text box to a multi-panel interface. This week, add an image upload tab. The user uploads a photo, and the app runs the full week 1–7 pipeline and shows the result."

Probe:
- "Use `st.tabs` to add a second tab: 'Text input' (what exists) and 'Photo input' (new). What changes between the two paths — just the entry point, or does anything downstream differ?"
- "Show the uploaded image in the app alongside the extraction output. What fields do you display — just the recipe name, or the full extracted ingredients and directions too?"
- "What does the app show if extraction fails? An error message, or the raw model output for debugging?"
- "Is there anything the photo input reveals that the user *couldn't* have typed — information visible in the image that they'd be unlikely to transcribe manually?"

The week 7 Streamlit target: a `st.tabs` layout with 'Text input' and 'Photo input' tabs. The photo tab accepts an uploaded image, runs `extract_from_image()`, shows the extracted fields, then feeds through the full pipeline and shows the personalised result — the same output the text tab produces, but from a photo.

---

## What to capture in the spec

Once the student has addressed all six areas, the implementation spec should include:

- **Visual input**: what the user provides and what it contains
- **Extraction schema**: the exact JSON fields extracted from the image, with one worked example
- **Pipeline connection**: which existing component receives the extraction output and whether any transformation is needed
- **Evaluation plan**: one test case (image → expected extraction) and the metric for the full pipeline
- **Problem statement update**: whether the week 1 problem statement changes with visual input, and if so, the revised version
- **Full pipeline description**: start-to-finish walkthrough of the updated system, naming each component from weeks 1–7
