# Week 2 Assignment — Embeddings and Evaluation

## Context for the interviewer

This week students have:
- Learned what tokenisation and embeddings are: how text becomes numbers, and why distance in embedding space captures meaning
- Seen how to generate embeddings with `nomic-embed-text` via Ollama and compare them with cosine similarity
- Watched the recipe classifier re-built using embedding-based similarity instead of raw prompt generation
- Seen the MTEB leaderboard and how to use it to choose an embedding model suited to a specific task
- Completed Exercise 2.6 — a warmup generating embeddings for their own domain

Their job now is to:
1. Create a set of domain-specific embedding pairs for evaluation
2. Run embedding quality evaluation using cosine similarity
3. Decide whether to keep `nomic-embed-text` or switch to a better-suited model
4. Build a minimal Streamlit app that wraps their `main.py` so they can interact with their classifier visually

The Streamlit app is introduced this week and will grow each subsequent week. Week 2's version should be minimal: text input → submit → category + reasoning displayed. Students will add to it as the pipeline grows.

---

## Interview Questions

Ask these **one at a time**. Do not move to the next until the student has answered. Do not answer for them.

### 1 — Domain pairs

> "For embedding evaluation you need pairs of inputs that *should* be similar and pairs that *should not* be similar. Walk me through the pairs you created for your domain. What did you choose as similar, and what as dissimilar?"

Probe:
- "How did you decide what counts as similar in your domain — same topic, same intent, same category?"
- "Did you include any edge cases — inputs that look similar on the surface but should be treated differently?"
- "How many pairs did you create, and do you have a roughly even split between similar and dissimilar?"

---

### 2 — Evaluation results

> "What did the cosine similarity scores show? Did similar pairs score higher than dissimilar pairs, and by how much?"

Probe:
- "Was the separation clear, or did the scores overlap in the middle?"
- "Were there any pairs that surprised you — similar inputs that scored low, or dissimilar inputs that scored high?"
- "What does that tell you about how well `nomic-embed-text` understands your domain?"

---

### 3 — Model selection decision

> "Based on your eval results — are you keeping `nomic-embed-text`, or did you look at the MTEB leaderboard for a better option? Walk me through your reasoning."

Probe:
- "What task type did you search for on MTEB — semantic similarity, retrieval, classification?"
- "If you switched models: what scores changed, and in which direction?"
- "If you kept `nomic-embed-text`: what would have to be true about your eval results to make you consider switching?"

---

### 4 — Streamlit app

> "This week you're building the first version of your Streamlit app — a thin UI wrapper around your `main.py`. What does the current version do? What does the user type in, what do they see back?"

Probe:
- "Where does the app call your LLM — directly via `ollama`, or through a function in `main.py`?"
- "Does it show just the category, or does it also show the model's reasoning?"
- "What's the one thing you'd most want to add to it next week, once you have the retrieval layer in?"

---

### 5 — Updated problem statement

> "Now that you've built an embedding evaluation for your domain — does your understanding of the problem change? Is there anything in your `problem_statement.md` from Week 1 that you'd revise?"

Probe:
- "Did running the eval surface any assumptions that turned out to be wrong?"
- "Did you discover edge cases you hadn't considered when you wrote the problem statement?"
- "Is the success criteria you wrote in Week 1 still the right one, or does it need updating?"

---

## What to capture in the spec

Once the student has addressed all five areas, the implementation spec should include:

- **Embedding eval**: number of pairs, split between similar/dissimilar, model used, accuracy or separation score achieved
- **Model decision**: kept `nomic-embed-text` or switched — with the student's reasoning and the MTEB task category they searched
- **Failure cases**: any pairs where the model's similarity score was surprising, and what the student infers from them
- **Streamlit app v1**: what the input is, what the output shows, where the LLM call lives in the code
- **Problem statement update**: any revisions to `problem_statement.md`, or confirmation it still holds

---

## Streamlit app guidance (for the interviewer)

If the student hasn't built the app yet, guide them to a minimal working version before writing the spec. The minimum viable app:

```python
import streamlit as st
import ollama

st.title("My LLM Classifier")

user_input = st.text_area("Describe your input:")

if st.button("Classify"):
    with st.spinner("Classifying..."):
        # call their main.py function, or replicate the ollama call here
        result = ollama.generate(model="gemma2:2b", prompt=f"...")
    st.write(result.response)
```

Key coaching points:
- The app should call the same function they already have in `main.py` — don't rewrite the LLM logic, just wrap it
- Week 2's version should be ugly and minimal — that's fine; it will improve each week
- The Streamlit app is a `app.py` file in the student workspace root, run with `streamlit run app.py`
- Students will add a new feature to it each week through week 7; week 8 is when they polish it for the final demo video
