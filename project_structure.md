# Project Structure

This document explains the layout of your student scaffolding and the reasoning behind it.

```
student_scaffolding/
├── .claude/
│   └── skills/
│       └── setup-debugger/
├── data/
│   └── All_Recipe_Web_Scraping_Dataset_Labeled.csv
├── notebooks/
│   └── .gitkeep
├── prompts/
│   └── .gitkeep
├── src/
│   └── baseline_recipe_classifier/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.yaml
│       └── evaluate.py
├── .env.example
├── .python-version
├── CLAUDE.md
├── project_structure.md   ← you are here
├── pyproject.toml
├── README.md
```

---

## Folder by Folder

### `src/baseline_recipe_classifier/`

The Python package you start with and progressively improve. It is structured as a proper importable package so that:
- `uv run python -m baseline_recipe_classifier "Dish Name"` works from the project root.
- Claude Code agents can read and extend it incrementally across all 8 weeks.
- You can add new modules alongside the existing ones without breaking imports.

Key files:
- `__main__.py` — CLI entry point and core prediction logic.
- `config.yaml` — Swap the Ollama model or category definitions here.
- `evaluate.py` — Ablation study runner (baseline vs. context-enhanced).

### `data/`

Houses the recipe dataset. The CSV contains 13,057 recipes scraped from AllRecipes, with time-based category labels (A–E) pre-computed.

The dataset is checked in here (not in `src/`) so that in later weeks you can swap it for a custom dataset without touching the source code.

### `notebooks/`

Placeholder folder for weekly Jupyter notebooks. Each week's notebook is distributed separately and should be placed here. The `.gitkeep` file ensures the empty folder is tracked by git.

The notebooks are educational — they show patterns and techniques. They are not solutions.

### `prompts/`

Contains the weekly personalization prompt files (e.g., `week1_problem_statement_prompt.md`). These are instructor-provided interview questions that guide your design decisions. The generated YAML specs are saved to `specs/`, not here.

### `.claude/skills/`

Contains skill definitions for Claude Code. The `setup-debugger/` skill provides automated environment triage — invoke it from Claude Code when something isn't working.

This folder follows the Claude Code skills spec — each skill lives in its own subdirectory with a `SKILL.md` file.

### `pyproject.toml`

Defines the project as a Python package managed by [uv](https://docs.astral.sh/uv/). All dependencies (Ollama client, PyYAML, ipykernel, pandas) are listed here.

Run `uv sync` to install/update dependencies. Run `uv run <command>` to execute commands inside the virtual environment without activating it manually.

### `.python-version`

Tells uv (and pyenv) which Python version to use. Pinned to 3.13 to match the course environment.

### `CLAUDE.md`

Instructions for Claude Code agents operating in this project. It points agents to `project_structure.md` (this file) and `agents.md` for context before they start making changes.

### `.env.example`

Template for environment variables. Copy to `.env` and fill in your API key if you want to use Claude-based features (the debug agent uses the `claude` CLI, not the API directly, so the key is optional for most workflows).

---

## Why This Layout?

1. **`src/` layout** keeps the package importable and isolates source code from data and config.
2. **Separate `data/` and `notebooks/`** allow you to swap datasets and receive new notebooks each week without merge conflicts.
3. **`specs/`** creates a clear boundary between your design decisions and the implementation — the AI agent reads your spec but doesn't write to it.
4. **`.claude/agents/`** makes environment debugging self-service — students don't need to describe their environment; the agent inspects it directly.
5. **`pyproject.toml` at the root** (not inside `src/`) means a single `uv sync` from the project root installs everything, matching the standard Python project convention.
