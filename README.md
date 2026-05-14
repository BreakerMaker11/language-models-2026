# Foundations of Language Models — Student Scaffolding

Welcome to the hands-on portion of the Foundations of Language Models course. This folder is your personal project workspace. Over 8 weeks you will extend the baseline recipe classifier, adding progressively more sophisticated ML techniques.

## What's Inside

| Folder/File | Purpose |
|---|---|
| `src/baseline_recipe_classifier/` | Starting-point classifier (zero-shot with Ollama) |
| `data/` | Recipe dataset (13,057 labeled recipes) |
| `notebooks/` | Drop your weekly Jupyter notebooks here |
| `prompts/` | Drop personalization prompt outputs here |
| `.claude/skills/setup-debugger/` | AI debug agent for environment issues |
| `pyproject.toml` | Python project & dependency config (managed by uv) |

See `project_structure.md` for a deeper explanation of the layout.

---

## Prerequisites

- **Python 3.11+** (the setup script handles the venv via `uv`)
- **Ollama** installed and running locally
  - Download: <https://ollama.ai>
  - Pull the default model: `ollama pull gemma2:2b`
- **uv** — install from <https://docs.astral.sh/uv/getting-started/installation/>
- **rclone** — required for uploading files to Google Drive (for Colab)
  - Install: <https://rclone.org/install/>
  - Configure Google Drive once: `rclone config create gdrive drive` — opens a browser for OAuth login; just click Allow
  - Token is stored at `~/.config/rclone/rclone.conf` and auto-renews; login is only needed once
- **claude CLI** — will be needed through out the course
  - Install: <https://claude.ai/code>

---

## Colab Setup

You need the repo files in your Colab environment to run notebooks without missing data. The recommended route:

1. Make sure `rclone` is installed and the `gdrive` remote is configured (see Prerequisites above)
2. Run the upload script once from the repo root:
   ```bash
   ./upload_to_colab.sh
   ```
   This copies notebooks, data, and dependency files to `watspeed_llm_course/` in your Google Drive.
3. In Colab, mount Drive and set your working directory to `/content/drive/MyDrive/watspeed_llm_course`
4. Open any notebook from the `notebooks/` folder and run it

---

## Local Setup

1. Get the repo
```bash
# 1. Clone the repo and cd into it
git clone https://github.com/Aggregate-Intellect/watspeed-llm-course-student-repo.git

cd watspeed-llm-course-student-repo   # or wherever you placed it
```

2. Setup Claude Code

using their quickstart https://code.claude.com/docs/en/quickstart

**Assisted Setup**
- Launch Claude Code
- run `/setup-debugger` this is a helper skill that will make sure your repository is setup properly

**Manual Setup**

- Install uv (if not already installed)
`curl -LsSf https://astral.sh/uv/install.sh | sh`

- Install Ollama (if not already installed)
`curl -fsSL https://ollama.ai/install.sh | sh`

- Start Ollama
`ollama serve &`

- Install rclone (if not already installed)
`curl https://rclone.org/install.sh | sudo bash`
_(Mac with Homebrew: `brew install rclone`)_

- Configure Google Drive access (one-time)
`rclone config create gdrive drive`
_(opens browser for Google OAuth — just click Allow)_

- Install project dependencies
`uv sync`

- Pull the model (first time only)
`ollama pull gemma2:2b`

- Test the classifier
`uv run python -m baseline_recipe_classifier "Chicken Souvlaki"`


Expected output:
```
Loaded dataset with 13057 recipes
Classifying: Chicken Souvlaki
Using model: gemma2:2b
Mode: context-enhanced

Predicted Category: D
Category Name: Short Wait
Description: Wait time 1-30 min (rest, marinate, chill)
```
---


## Weekly Workflow

Each week follows the same three-step pattern:

1. **Notebook** — Open the weekly notebook in Google Colab (or locally). Read through the concepts and run the examples. The notebook showcases concepts, ideas and core workflows that are essential, not complete solutions.

2. **Personalization prompt** — Run the week's personalization prompt in Claude (or another AI assistant). It will interview you about design decisions and output an implementation spec as YAML.

3. **Implement with Claude Code** — Use the spec generated to do your implementation with claude code. Make sure to probe it's choices and not let it lead your way all the time for an effective learning experience.

---

## Claude Code Agents

This project includes specialised Claude Code commands, agents that are designed to assist with different parts of the workflow. These are automatically loaded into claude via `.claude` folder in the repo:

```
Use the assignment-partner agent
```

### Available Commands and Agents

| Agent | When to use |
|---|---|
| `assignment-partner` | Start here each week. Interviews you about design decisions and generates an implementation spec (`specs/week<N>_implementation_specs.yaml`). |
| `setup-debugger` | Run when environment setup fails — broken Ollama, missing dataset, kernel errors, etc. |

---

## Troubleshooting

### `uv: command not found`
Install uv from <https://docs.astral.sh/uv/getting-started/installation/> then re-run `uv sync`.

### `ollama: command not found`
Install Ollama from <https://ollama.ai> and make sure it is running:
```bash
ollama serve &   # start in background
ollama pull gemma2:2b
```

### `Error calling Ollama: ...`
Ollama must be running before you call the classifier.
```bash
ollama serve
```

### Dataset not found warning
make sure `data/All_Recipe_Web_Scraping_Dataset_Labeled.csv` exists.

### Jupyter kernel not found
```bash
uv run python -m ipykernel install --user --name applied-ml-course
```

### Still stuck?
Run the setup debugger agent (requires `claude` CLI):

```
Use the setup-debugger agent
```

The agent will check your Python version, uv, Ollama, dataset, and run a test prediction, then print a summary of what passed and exactly how to fix any failures.
