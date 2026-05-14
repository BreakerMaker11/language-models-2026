# Cloud Code Templates

## requirements.txt

```
streamlit>=1.40.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
Pillow>=10.0.0
huggingface-hub>=0.24.0
peft>=0.10.0
scikit-learn>=1.3.0
pandas>=2.0.0
python-dotenv>=1.0.0
openai>=1.0.0
```

Omit: `ollama`, `accelerate`, `datasets`, `ipykernel`, `ipywidgets`, `notebook`, `pytest`, `transformers` — local-dev-only or adds 100s of MB for no cloud benefit.

---

## cloud_llm.py

Drop-in replacement for `ollama.generate(..., format="json")` calls in `main.py`.

```python
import os
from huggingface_hub import InferenceClient

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = InferenceClient(
            model="Qwen/Qwen2.5-7B-Instruct",
            token=os.environ.get("HF_TOKEN"),
        )
    return _client

def generate_json(prompt: str, system: str = "") -> str:
    """Returns the raw text response; caller does json.loads()."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = _get_client().chat_completion(
        messages=messages,
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content
```

---

## cloud_vision.py

Drop-in replacement for `vision/extract.py:extract_from_image()`. Uses Groq (OpenAI-compatible endpoint) — better free-tier coverage than HF for vision models.

```python
import os
import base64
import json
import re
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    return _client

def extract_from_image_cloud(image_bytes: bytes) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    response = _get_client().chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Extract the recipe from this image. Return JSON only — no markdown fences.\n"
                    "Required fields: title (string), ingredients (list of strings), "
                    "instructions (list of strings).\n"
                    "Optional: prep_time, cook_time, servings (strings)."
                )},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        temperature=0,
        max_tokens=2048,
    )
    raw = response.choices[0].message.content.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE).strip()
    parsed = json.loads(cleaned)
    missing = {"title", "ingredients", "instructions"} - {k for k in parsed if parsed[k]}
    if missing:
        raise ValueError(f"Extraction missing required fields: {', '.join(sorted(missing))}")
    return parsed
```

---

## cloud_embeddings.py

Drop-in replacement for `ollama.embeddings(model="nomic-embed-text", prompt=text).embedding`.

```python
from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
    return _model

def embed(text: str) -> list[float]:
    return get_model().encode(text, normalize_embeddings=True).tolist()
```

---

## Patching main.py

Add near the top:

```python
import os

def _is_cloud() -> bool:
    return bool(os.environ.get("HF_SPACE"))
```

In `rewrite_recipe()`, replace the `ollama.generate()` block:

```python
if _is_cloud():
    from cloud_llm import generate_json
    output = json.loads(generate_json(prompt, system_prompt))
else:
    result = ollama.generate(
        model="gemma2:2b", prompt=prompt, system=system_prompt, format="json"
    )
    output = json.loads(result.response)
```

Guard the adapter path:

```python
if use_adapter:
    if _is_cloud():
        raise FileNotFoundError(
            "Adapter not available in cloud deployment — use Prompt-only mode."
        )
    if not os.path.exists(ADAPTER_PATH):
        raise FileNotFoundError(
            f"Adapter not found at {ADAPTER_PATH}. Run finetuning/train.py --backend mps first."
        )
    ...
```

---

## Patching retrieval stores (dish_store.py, allergen_profile_store.py, vector_store.py)

Apply these two changes to each store file:

```python
import os

def _embed(text: str) -> list[float]:
    if os.environ.get("HF_SPACE"):
        from cloud_embeddings import embed
        return embed(text)
    return ollama.embeddings(model=EMBED_MODEL, prompt=text).embedding

def _make_client(persist_dir: str):
    if os.environ.get("HF_SPACE"):
        return chromadb.EphemeralClient()
    return chromadb.PersistentClient(path=persist_dir)
```

In each store's `__init__`, replace `chromadb.PersistentClient(path=persist_dir)` with `_make_client(persist_dir)`.

---

## Patching app.py

Replace the direct `extract_from_image()` call in the photo tab:

```python
def _extract(image_bytes: bytes) -> dict:
    if os.environ.get("HF_SPACE"):
        from cloud_vision import extract_from_image_cloud
        return extract_from_image_cloud(image_bytes)
    from vision.extract import extract_from_image
    return extract_from_image(image_bytes)
```

---

## README.md frontmatter block

```markdown
---
title: Allergy-Safe Recipe Assistant
emoji: 🍳
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
pinned: false
license: mit
---

# Allergy-Safe Recipe Assistant

Upload a recipe (text or photo) and get a safely rewritten version that removes your allergens —
with dish-aware substitutions and cooking history inference.

Built with Streamlit + ChromaDB + HF Inference API + Groq Vision.
```

---

## upload_to_hf.py

```python
import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv(".env")
token = os.environ.get("HF_TOKEN")
if not token:
    raise EnvironmentError("HF_TOKEN not found in .env — add it before uploading.")

api = HfApi(token=token)
api.upload_folder(
    folder_path=".",
    repo_id="YOUR_HF_USERNAME/allergy-safe-recipe-assistant",  # update this
    repo_type="space",
    ignore_patterns=[
        "finetuning/adapter/**", "finetuning/finetune_data.jsonl",
        "retrieval/chroma_db/**",
        ".venv/**", "**/__pycache__/**", "**/*.pyc",
        "notebooks/**", ".claude/**", "specs/**",
        "data/All_Recipe_Web_Scraping_Dataset_With_Directions.csv",
        "data/All_Recipe_Web_Scraping_Dataset_Labeled.csv",
        "data/finetune_option_a.jsonl", "data/finetune_option_b.jsonl",
        ".git/**", ".DS_Store", "**/.DS_Store",
    ],
    commit_message="deploy Allergy-Safe Recipe Assistant",
)
print("Upload complete! Space will build in 5–10 minutes.")
```
