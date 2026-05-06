#!/usr/bin/env bash
# Upload course materials to Google Drive for Google Colab access via rclone.
#
# Prerequisites:
#   rclone configured with a Google Drive remote (run `rclone config` once).
#
# Usage:
#   ./upload_to_colab.sh [REMOTE_NAME] [DRIVE_FOLDER]
#
# Defaults:
#   REMOTE_NAME  = gdrive
#   DRIVE_FOLDER = watspeed_llm_course

set -euo pipefail

REMOTE="${1:-gdrive}"
DRIVE_FOLDER="${2:-watspeed_llm_course}"
DEST="${REMOTE}:${DRIVE_FOLDER}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Uploading to ${DEST}"
echo "    Source: ${REPO_ROOT}"
echo

echo "[1/3] notebooks/"
rclone copy "${REPO_ROOT}/notebooks" "${DEST}/notebooks" \
  --exclude "__pycache__/**" --exclude "*.pyc" --exclude ".DS_Store" \
  --progress

echo "[2/3] data/"
rclone copy "${REPO_ROOT}/data" "${DEST}/data" \
  --exclude "raw_data/**" --exclude "data_prep/**" \
  --exclude "__pycache__/**" --exclude "*.pyc" --exclude ".DS_Store" \
  --progress

echo "[3/3] pyproject.toml + uv.lock"
rclone copyto "${REPO_ROOT}/pyproject.toml" "${DEST}/pyproject.toml" --progress
rclone copyto "${REPO_ROOT}/uv.lock"        "${DEST}/uv.lock"        --progress

echo
echo "Done. Files available at: ${DEST}"
echo "In Colab, mount Drive and set your working directory to /content/drive/MyDrive/${DRIVE_FOLDER}"
