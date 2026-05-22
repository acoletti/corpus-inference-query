#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="${VENV_DIR:-$repo_root/.venv}"
editable="${EDITABLE_INSTALL:-0}"

# Ensure uv is available
if ! command -v uv &> /dev/null; then
  echo "uv is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv venv "$venv_dir"

if [ "$editable" = "1" ]; then
  uv pip install -e "$repo_root"
else
  uv pip install "$repo_root"
fi

echo "Installed code-inference-query into $venv_dir"
echo "CLI available at $venv_dir/bin/code-inference-query"
