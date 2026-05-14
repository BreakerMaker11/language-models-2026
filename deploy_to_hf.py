"""
Deploy the Allergy-Safe Recipe Assistant to Hugging Face Spaces.

The local repo is never modified — all cloud patches are applied in a
temporary directory, uploaded from there, then discarded.

Prerequisites:
  1. HF account at huggingface.co + a Write-scope token
  2. Free Groq API key at console.groq.com
  3. Both keys in .env:  HF_TOKEN=...  and  GROQ_API_KEY=...
  4. Update HF_REPO below with your HF username

Usage:
  uv run python deploy_to_hf.py
"""

import os
import re
import shutil
import tempfile
import textwrap
from pathlib import Path
from dotenv import load_dotenv

# ── CONFIG — update your username ────────────────────────────────────────────
HF_REPO = "YOUR_HF_USERNAME/allergy-safe-recipe-assistant"
# ─────────────────────────────────────────────────────────────────────────────

SKIP = {
    "finetuning/adapter", "finetuning/finetune_data.jsonl",
    "retrieval/chroma_db", ".venv", "__pycache__", ".git",
    "notebooks", ".claude", "specs", ".DS_Store",
    ".env",
    "data/All_Recipe_Web_Scraping_Dataset_With_Directions.csv",
    "data/All_Recipe_Web_Scraping_Dataset_Labeled.csv",
    "data/finetune_option_a.jsonl", "data/finetune_option_b.jsonl",
    "deploy_to_hf.py",
}


def _skip(path: Path, root: Path) -> bool:
    rel = str(path.relative_to(root))
    return any(rel == p or rel.startswith(p + "/") for p in SKIP)


def _copy_project(src: Path, dst: Path):
    for item in src.rglob("*"):
        if _skip(item, src) or not item.is_file():
            continue
        target = dst / item.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def _write_cloud_files(dst: Path):
    (dst / "requirements.txt").write_text(textwrap.dedent("""\
        streamlit>=1.40.0
        chromadb>=0.5.0
        sentence-transformers>=3.0.0
        einops>=0.7.0
        Pillow>=10.0.0
        huggingface-hub>=0.24.0
        peft>=0.10.0
        scikit-learn>=1.3.0
        pandas>=2.0.0
        python-dotenv>=1.0.0
        openai>=1.0.0
    """))

    (dst / "cloud_llm.py").write_text(textwrap.dedent("""\
        import os
        import re
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
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = _get_client().chat_completion(
                messages=messages, temperature=0.1, max_tokens=2048,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            raw = re.sub(r'^```(?:json)?\\s*', '', raw, flags=re.MULTILINE)
            raw = re.sub(r'```\\s*$', '', raw, flags=re.MULTILINE).strip()
            # Extract JSON object if there's surrounding text
            match = re.search(r'\\{.*\\}', raw, re.DOTALL)
            return match.group(0) if match else raw
    """))

    (dst / "cloud_vision.py").write_text(textwrap.dedent("""\
        import os, base64, json, re
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
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": (
                        "Extract the recipe from this image. Return JSON only — no markdown fences.\\n"
                        "Required: title (string), ingredients (list), instructions (list).\\n"
                        "Optional: prep_time, cook_time, servings (strings)."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]}],
                temperature=0, max_tokens=2048,
            )
            raw = response.choices[0].message.content.strip()
            cleaned = re.sub(r'^```(?:json)?\\s*', '', raw, flags=re.MULTILINE)
            cleaned = re.sub(r'```\\s*$', '', cleaned, flags=re.MULTILINE).strip()
            parsed = json.loads(cleaned)
            missing = {"title", "ingredients", "instructions"} - {k for k in parsed if parsed[k]}
            if missing:
                raise ValueError(f"Extraction missing: {', '.join(sorted(missing))}")
            return parsed
    """))

    (dst / "cloud_embeddings.py").write_text(textwrap.dedent("""\
        from sentence_transformers import SentenceTransformer

        _model = None

        def get_model():
            global _model
            if _model is None:
                _model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
            return _model

        def embed(text: str) -> list[float]:
            return get_model().encode(text, normalize_embeddings=True).tolist()
    """))


def _patch_main(dst: Path):
    path = dst / "main.py"
    src = path.read_text()

    src = src.replace(
        "import json\nimport sys\nimport os\nimport ollama",
        "import json\nimport sys\nimport os\n\n"
        "def _is_cloud() -> bool:\n    return bool(os.environ.get('SPACE_ID'))\n\n"
        "if not _is_cloud():\n    import ollama\n",
    )

    old_gen = (
        "        result = ollama.generate(\n"
        "            model=\"gemma2:2b\",\n"
        "            prompt=prompt,\n"
        "            system=system_prompt,\n"
        "            format=\"json\",\n"
        "        )\n"
        "        output = json.loads(result.response)"
    )
    new_gen = (
        "        if _is_cloud():\n"
        "            from cloud_llm import generate_json\n"
        "            output = json.loads(generate_json(prompt, system_prompt))\n"
        "        else:\n"
        "            result = ollama.generate(\n"
        "                model=\"gemma2:2b\",\n"
        "                prompt=prompt,\n"
        "                system=system_prompt,\n"
        "                format=\"json\",\n"
        "            )\n"
        "            output = json.loads(result.response)"
    )
    if old_gen not in src:
        raise ValueError("_patch_main: ollama.generate block not found — indentation mismatch")
    src = src.replace(old_gen, new_gen)

    # Disable adapter on cloud (it's not uploaded)
    src = src.replace(
        "    if use_adapter:\n        if not os.path.exists(ADAPTER_PATH):",
        "    if use_adapter:\n        if _is_cloud() or not os.path.exists(ADAPTER_PATH):",
    )

    path.write_text(src)


def _patch_retrieval(dst: Path):
    cloud_embed = (
        "def _embed(text: str) -> list[float]:\n"
        "    if os.environ.get('SPACE_ID'):\n"
        "        from cloud_embeddings import embed\n"
        "        return embed(text)\n"
        "    return ollama.embeddings(model=EMBED_MODEL, prompt=text).embedding"
    )
    for name in ["dish_store.py", "allergen_profile_store.py", "vector_store.py"]:
        path = dst / "retrieval" / name
        if not path.exists():
            continue
        src = path.read_text()
        src = src.replace(
            "import ollama",
            "if not os.environ.get('SPACE_ID'):\n    import ollama",
        )
        src = re.sub(
            r"def _embed\(text: str\) -> list\[float\]:\n"
            r"    return ollama\.embeddings\(model=EMBED_MODEL, prompt=text\)\.embedding",
            cloud_embed,
            src,
        )
        src = src.replace(
            "chromadb.PersistentClient(path=persist_dir)",
            "(chromadb.EphemeralClient() if os.environ.get('SPACE_ID')"
            " else chromadb.PersistentClient(path=persist_dir))",
        )
        path.write_text(src)


def _patch_vision(dst: Path):
    path = dst / "vision" / "extract.py"
    if not path.exists():
        return
    src = path.read_text()
    src = src.replace(
        "import ollama",
        "if not os.environ.get('SPACE_ID'):\n    import ollama",
    )
    # add os import if not already present
    if "import os" not in src:
        src = "import os\n" + src
    path.write_text(src)


def _patch_app(dst: Path):
    path = dst / "app.py"
    src = path.read_text()
    src = src.replace(
        "from vision.extract import extract_from_image, extracted_to_recipe_text",
        "import os as _os\n"
        "if _os.environ.get('SPACE_ID'):\n"
        "    from cloud_vision import extract_from_image_cloud as extract_from_image\n"
        "else:\n"
        "    from vision.extract import extract_from_image\n"
        "from vision.extract import extracted_to_recipe_text",
    )
    path.write_text(src)


def _write_readme(dst: Path):
    (dst / "README.md").write_text(textwrap.dedent("""\
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

        Upload a recipe (text or photo) and get a safely rewritten version
        that removes your allergens — with dish-aware substitutions and
        cooking history inference.

        Built with Streamlit + ChromaDB + HF Inference API + Groq Vision.
    """))


def _upload(src_dir: Path):
    from huggingface_hub import HfApi
    load_dotenv(".env")
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise EnvironmentError(
            "HF_TOKEN not found in .env — add it before deploying.\n"
            "Get a Write-scope token at huggingface.co → Settings → Access Tokens."
        )
    api = HfApi(token=token)
    print(f"\nUploading to {HF_REPO} ...")
    api.upload_folder(
        folder_path=str(src_dir),
        repo_id=HF_REPO,
        repo_type="space",
        commit_message="deploy Allergy-Safe Recipe Assistant",
    )
    print(f"\nDone! Space will build in 5–10 minutes.")
    print(f"URL: https://huggingface.co/spaces/{HF_REPO}")
    print("\nIf the app crashes on first load, check Space → Settings → Secrets:")
    print("  HF_TOKEN   — your HF Write token")
    print("  GROQ_API_KEY — free key from console.groq.com")


def main():
    if "YOUR_HF_USERNAME" in HF_REPO:
        print("ERROR: Open deploy_to_hf.py and replace YOUR_HF_USERNAME with your HF username.")
        return

    root = Path(__file__).parent

    with tempfile.TemporaryDirectory(prefix="hf_deploy_") as tmp:
        dst = Path(tmp)

        print("Copying project files to temp directory...")
        _copy_project(root, dst)

        print("Writing cloud adapter files (cloud_llm, cloud_vision, cloud_embeddings)...")
        _write_cloud_files(dst)

        print("Patching main.py for HF Inference API...")
        _patch_main(dst)

        print("Patching retrieval stores (embeddings + ChromaDB)...")
        _patch_retrieval(dst)

        print("Patching vision/extract.py for cloud...")
        _patch_vision(dst)

        print("Patching app.py for cloud vision...")
        _patch_app(dst)

        print("Writing README with HF Space frontmatter...")
        _write_readme(dst)

        _upload(dst)
        # temp dir cleaned up automatically


if __name__ == "__main__":
    main()
