---
name: host-streamlit
description: Deploys the Allergy-Safe Recipe Assistant to Hugging Face Spaces (free public hosting). TRIGGER when the student asks to host, deploy, share, or get a public URL for their app.
---

You are guiding a student through publishing their Allergy-Safe Recipe Assistant to HF Spaces as an optional course showcase. Work through three phases in order, one step at a time — wait for confirmation before each transition.

**Your local project is completely safe.** `deploy_to_hf.py` works entirely in a temporary directory:
1. Copies your project files there (excluding `.env` and secrets)
2. Applies all cloud patches in the temp copy
3. Uploads from the temp copy to your Space
4. Deletes the temp directory

Nothing in your local repo is ever modified or exposed.

---

## Phase 1 — Prerequisites

### 1a — HF token
Ask:
> "You'll need a Write-scope HF token for this. It takes about 1 minute:
> 1. Go to huggingface.co and log in
> 2. Click your profile picture (top right) → **Settings**
> 3. In the left sidebar, click **Access Tokens**
> 4. Click **New Token** → give it a name (e.g. `allergy-recipe-deploy`) → set Role to **Write**
> 5. Click **Generate token**, copy it
> 6. Add it to your `.env` file as `HF_TOKEN=your_token_here`"

Do not proceed until confirmed.

### 1b — Groq API key (for vision)
Ask:
> "Do you have a Groq API key? It's free and takes about 2 minutes to get:
> 1. Go to console.groq.com
> 2. Sign up or log in (no credit card needed)
> 3. Click **API Keys** in the left sidebar → **Create API Key**
> 4. Give it a name (e.g. `allergy-recipe-app`), copy the key
> 5. Add it to your `.env` file as `GROQ_API_KEY=your_key_here`"

Do not proceed until confirmed.

### 1c — Confirm .env has both keys
Run:
```bash
uv run python -c "
from dotenv import load_dotenv; import os
load_dotenv('.env')
missing = [k for k in ['HF_TOKEN','GROQ_API_KEY'] if not os.environ.get(k)]
print('OK — both keys found' if not missing else f'MISSING: {missing}')
"
```
Expected output: `OK — both keys found`. If missing, ask the student to check their `.env` file.

---

## Phase 2 — Create the Space & set secrets

Walk through each step, waiting for confirmation:

**Step 1 — Create the Space**
> "Go to huggingface.co/new-space and fill in the form:
> 1. **Owner** — select your username from the dropdown
> 2. **Space name** — type `<your-app-name>` (e.g. `allergy-safe-recipe-assistant`, or any name you like)
> 3. **License** — select MIT
> 4. **Select the Space SDK** — you'll see a row of options: Static, Gradio, Streamlit, Docker, Custom. Click **Streamlit**.
> 5. **Space hardware** — leave it on the default free CPU
> 6. **Visibility** — select **Public**
> 7. Click **Create Space**"

**Step 2 — Add secrets to the Space**
> "In your new Space → Settings → Variables and Secrets → New Secret:
> - Name: `HF_TOKEN`, Value: your HF Write token
> - Name: `GROQ_API_KEY`, Value: your Groq key
>
> These are different from your local `.env` — the Space needs its own copies."

**Step 3 — Update your HF username in the deploy script**

Open `deploy_to_hf.py` and replace `YOUR_HF_USERNAME` on line 1 with your actual HF username:
```python
HF_REPO = "your-username/<your-app-name>"
```

---

## Phase 3 — Deploy & verify

**Deploy:**
```bash
uv run python deploy_to_hf.py
```

The script will:
1. Copy project files to a temp directory
2. Apply all cloud patches (swaps Ollama → HF Inference API + Groq, ChromaDB → EphemeralClient)
3. Upload to your Space
4. Delete the temp directory

First build takes 5–10 minutes. The URL will be printed when upload completes — it matches whatever Space name you chose in Phase 2.

**Verify:**
Once the build finishes, open the Space URL (printed by the script above) and test:
1. Text input tab: paste a recipe, confirm allergen inference and rewrite work
2. Photo input tab: upload the `data/sample_recipes/taco_bake_recipe_card.png` image, confirm extraction and rewrite work

---

## Error Quick-Reference

| Symptom | Fix |
|---|---|
| `HF_TOKEN not found in .env` | Add `HF_TOKEN=...` to your local `.env` |
| `Bad request — offending files: .env` | `.env` was included in upload; update deploy_to_hf.py SKIP set to include `".env"` |
| `YOUR_HF_USERNAME` in error | Update `HF_REPO` in `deploy_to_hf.py` |
| `HF_TOKEN not set` (Space crash) | Space → Settings → Secrets → add HF_TOKEN |
| `GROQ_API_KEY not set` (Space crash) | Space → Settings → Secrets → add GROQ_API_KEY |
| Space sleeping | Normal on free tier — first visit wakes it in ~30s |
| `Module not found` on Space | Add `sys.path.insert(0, ".")` at top of `app.py` in `deploy_to_hf.py`'s `_patch_app()` |
| `ModuleNotFoundError: No module named 'ollama'` | `import ollama` must be conditional — update `_patch_main()` in `deploy_to_hf.py` to wrap it: `if not _is_cloud(): import ollama` |
| `model_decommissioned` (Groq vision error) | Update vision model in `deploy_to_hf.py` `_write_cloud_files()` — current model: `meta-llama/llama-4-scout-17b-16e-instruct` |
| Build fails with dependency error | Check Space logs → Settings → Logs; report the error for help |
