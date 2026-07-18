#!/usr/bin/env bash
# Serial bakeoff: all gemma4 cards → unload → all qwen3 cards
set -euo pipefail

export OLLAMA_HOST=http://100.85.195.54:11434

echo "=== [1/4] gemma4:12b — all-dev ==="
uv run --no-sync python main.py --all-dev

echo ""
echo "=== [2/4] Unloading gemma4:12b ==="
ollama stop gemma4:12b && echo "gemma4:12b unloaded" || echo "(ollama stop not supported — relying on keep_alive expiry)"

echo ""
echo "=== [3/4] qwen3:14b — all-dev ==="
uv run --no-sync python main.py --all-dev --model qwen3:14b

echo ""
echo "=== [4/4] Unloading qwen3:14b ==="
ollama stop qwen3:14b && echo "qwen3:14b unloaded" || true

echo ""
echo "=== Bakeoff complete ==="
