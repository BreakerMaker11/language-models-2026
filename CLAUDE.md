# Applied ML Course — Student Project

This is the student workspace for the 8-week Applied ML course. You are building and extending a recipe time classifier across the course.

## Essential Reading

Before making any changes, read these files in order:

1. `project_structure.md` — Explains every folder and file in this project and why it is structured that way.
2. `README.md` — Quick start, prerequisites, and weekly workflow.

## Project Summary

**Goal**: A repository for students taking the course to start in 
**Technology**: Python + Ollama (local LLM) + uv (package manager).

**Key files**:
- `
- `data/All_Recipe_Web_Scraping_Dataset_Labeled.csv` — 13,057 labeled recipes.

## Working With This Project

### Running the classifier
```bash
uv run python -m baseline_recipe_classifier "Chicken Souvlaki"
```

### Running evaluation
```bash
uv run python -m baseline_recipe_classifier.evaluate --num-samples 20 --verbose
```

### Installing dependencies
```bash
uv sync
```

## Weekly Extension Pattern

Each week you will:
1. Receive a Jupyter notebook (place it in `notebooks/`).
2. Run the personalization prompt and save the YAML spec to `prompts/`.
3. Ask Claude Code to implement the spec by extending `src/baseline_recipe_classifier/`.

When implementing: adapt patterns from the notebook to the spec — do not copy notebook code directly.

## Python Commands

Always use `uv run` instead of `python` directly. Never activate the virtualenv manually.

```bash
# Correct
uv run python script.py
uv run pytest

# Wrong
python script.py
source .venv/bin/activate && python script.py
```

## Coding Conventions

- Keep all new Python code inside `src/baseline_recipe_classifier/` or new sub-packages alongside it.
- Keep configuration changes in `config.yaml` rather than hardcoding values.
- Do not modify `data/` or `notebooks/` — treat them as read-only inputs.
- Do not add time-related fields as context to the classifier (this would leak the label).

## Debug Skill

If the environment is broken, run in claude cli:

```
Use setup-debugger skill to fix the environment
```

This triggers the `setup-debugger` skill (see `.claude/skills/setup-debugger/setup-debugger.md`) which inspects your environment and provides exact fix commands.
