#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure uv is available
if ! command -v uv &> /dev/null; then
  echo "uv is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" \
  uv run --python "$(which python3)" pytest "$repo_root/tests" -v
