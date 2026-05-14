"""
Deterministically collect student project context.
Run from the student_scaffolding project root.
Outputs structured JSON to stdout.
"""
import json
import os
import sys
from pathlib import Path


def collect_notebooks(root: Path) -> list[str]:
    nb_dir = root / "notebooks"
    if not nb_dir.is_dir():
        return []
    return sorted([f.name for f in nb_dir.iterdir() if f.suffix == ".ipynb"])


def collect_src_files(root: Path) -> list[str]:
    src_dir = root / "src"
    if not src_dir.is_dir():
        return []
    files = []
    for f in sorted(src_dir.rglob("*")):
        if f.is_file() and not any(p.startswith("__pycache__") for p in f.parts):
            files.append(str(f.relative_to(src_dir)))
    return files


def check_src_changes(root: Path) -> bool:
    """Return True if NO student changes detected (baseline only)."""
    src_dir = root / "src"
    if not src_dir.is_dir():
        return True  # No src at all = no changes

    # Check git status for modifications in src/
    try:
        import subprocess
        result = subprocess.run(
            # Find the initial baseline commit (oldest ancestor)
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            capture_output=True, text=True, cwd=root
        )
        base_commit = result.stdout.strip() if result.returncode == 0 else None

        # Check if student files differ from baseline (committed changes count)
        student_paths = ["src/", "main.py", "app.py", "retrieval/", "eval/", "finetuning/", "vision/"]
        if base_commit:
            diff = subprocess.run(
                ["git", "diff", "--name-only", base_commit, "HEAD", "--"] + student_paths,
                capture_output=True, text=True, cwd=root
            )
            if diff.returncode == 0 and diff.stdout.strip():
                return False  # Student has made commits on top of baseline

        # Also check uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain", "--"] + student_paths,
            capture_output=True, text=True, cwd=root
        )
        if status.returncode == 0 and status.stdout.strip():
            return False  # Uncommitted changes present
        return True  # No changes from baseline detected
    except Exception:
        return False  # Can't determine — assume changes exist to avoid false warnings


def collect_data_files(root: Path) -> list[str]:
    data_dir = root / "data"
    if not data_dir.is_dir():
        return []
    return sorted([
        f.name for f in data_dir.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ])


def collect_problem_statement(root: Path) -> dict:
    ps_path = root / "problem_statement.md"
    if not ps_path.exists():
        ps_path = root / "problem-statement.md"
    if not ps_path.exists():
        return {"present": False}
    try:
        lines = ps_path.read_text().splitlines()[:5]
        return {"present": True, "first_lines": lines}
    except Exception:
        return {"present": True, "first_lines": []}


def collect_past_plans(root: Path) -> list[str]:
    # Check project-local plans first, then fall back to global
    local_plans = root / ".claude" / "plans"
    if local_plans.is_dir():
        return sorted([f.name for f in local_plans.iterdir() if f.is_file()])
    global_plans = Path.home() / ".claude" / "plans"
    if not global_plans.is_dir():
        return []
    return sorted([f.name for f in global_plans.iterdir() if f.is_file()])


def main():
    root = Path.cwd()

    notebooks = collect_notebooks(root)
    src_files = collect_src_files(root)
    no_src_changes = check_src_changes(root)
    data_files = collect_data_files(root)
    problem_statement = collect_problem_statement(root)
    past_plans = collect_past_plans(root)

    state_flags = {
        "NO_SRC_CHANGES": no_src_changes,
        "MISSING_PROBLEM_STATEMENT": not problem_statement["present"],
        "NO_PAST_PLANS": len(past_plans) == 0,
    }

    output = {
        "notebooks": notebooks,
        "src_files": src_files,
        "data_files": data_files,
        "problem_statement": problem_statement,
        "past_plans": past_plans,
        "state_flags": state_flags,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
