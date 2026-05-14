---
name: setup-debugger
description: Diagnose and fix environment setup issues so the first notebook runs successfully. TRIGGER when: the student says the environment is broken, uv sync fails, Ollama isn't available or won't connect, the classifier throws errors, Jupyter can't find the kernel, or asks to "debug setup" / "fix my environment".
allowed-tools: [Bash, Read, Glob, Grep]
model: sonnet
---

Systematically check every component of the student's environment and report exactly what is broken and how to fix it.

## How to run

Read `references/checks.md` for the full 10-check list with commands, pass/fail criteria, and fix commands.

Run all checks in order from the project root (the folder containing `pyproject.toml`). For each check, print a clear PASS or FAIL line with the fix command if it failed.

## Key rules

- If Ollama fails, mark classifier smoke test as SKIP (don't fail it separately).
- If rclone is not installed, mark gdrive remote check as SKIP.
- Keep fix commands copy-pasteable — use exact commands, not descriptions.
- Do not modify any project files. Only read and run diagnostic commands.
- Print a summary table at the end with all check statuses and required actions.
