# Environment Checks Reference

## 1. Python Version
```bash
uv run python --version
```
- PASS if version is 3.11 or higher.
- FAIL if lower or not found. Fix: `uv python install 3.13`

## 2. uv Installation
```bash
uv --version
```
- PASS if uv is found.
- FAIL if not found. Fix: `curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc`

## 3. uv Sync (Dependencies)
```bash
uv sync
```
- PASS if exits with code 0.
- FAIL if any errors. Print the full error and suggest: check internet connection, re-run `uv sync`, or check pyproject.toml for syntax errors.

## 4. Ollama Running
```bash
ollama list
```
- PASS if returns a list (even empty).
- FAIL if "connection refused" or command not found.
  - If not installed: Fix: `curl -fsSL https://ollama.ai/install.sh | sh`
  - If not running: Fix: `ollama serve &`

## 5. gemma2:2b Model Available
From the output of `ollama list`, check whether `gemma2:2b` appears.
- PASS if present.
- FAIL if missing. Fix: `ollama pull gemma2:2b`

## 6. Dataset Exists
```bash
ls -lh data/All_Recipe_Web_Scraping_Dataset_Labeled.csv
```
- PASS if file found and size > 1MB.
- FAIL if missing. Fix: Re-download the student scaffolding ZIP and re-extract.

## 7. Classifier Smoke Test
```bash
uv run python -m baseline_recipe_classifier "Scrambled Eggs"
```
- PASS if output contains "Predicted Category:" followed by A, B, C, D, or E.
- FAIL if any exception or "Failed to predict category". Print the full error.

## 8. Jupyter Kernel
```bash
uv run python -c "import ipykernel; print(ipykernel.__version__)"
```
- PASS if prints a version number.
- FAIL if ModuleNotFoundError. Fix: `uv add ipykernel && uv run python -m ipykernel install --user --name baseline-recipe-classifier`

## 9. rclone Installed
```bash
rclone --version
```
- PASS if found.
- FAIL if not found. Detect the OS and print the appropriate install command:
  - Linux: `curl https://rclone.org/install.sh | sudo bash`
  - macOS with Homebrew: `brew install rclone`
  - macOS without Homebrew: `curl https://rclone.org/install.sh | sudo bash`

## 10. Google Drive Remote Configured
```bash
rclone listremotes
```
- SKIP if Check 9 (rclone installed) failed.
- PASS if output contains `gdrive:`.
- FAIL if `gdrive:` is not listed. Fix: `rclone config create gdrive drive`

## Output Format

```
=== Setup Diagnostics Summary ===

CHECK                         STATUS   FIX COMMAND
--------------------------    ------   -----------
Python >= 3.11                PASS
uv installed                  PASS
uv sync (dependencies)        PASS
Ollama running                FAIL     ollama serve &
gemma2:2b model               FAIL     ollama pull gemma2:2b
Dataset exists                PASS
Classifier smoke test         SKIP     (blocked by Ollama)
Jupyter kernel                PASS
rclone installed              PASS
gdrive remote configured      FAIL     rclone config create gdrive drive

=== Action Required ===
1. Run: ollama serve &
2. Run: ollama pull gemma2:2b
3. Re-run: uv run python -m baseline_recipe_classifier "Scrambled Eggs"
```

If everything passes:
```
All checks passed. Your environment is ready!
Run: uv run python -m baseline_recipe_classifier "Chicken Souvlaki"
```
