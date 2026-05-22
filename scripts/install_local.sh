#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="${VENV_DIR:-$repo_root/.venv}"

# Ensure uv is available
if ! command -v uv &> /dev/null; then
  echo "uv is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv venv --allow-existing "$venv_dir"

uv pip install --python "$venv_dir" -e "$repo_root"

echo "Installed corpus-inference-query into $venv_dir"
echo "CLI available at $venv_dir/bin/corpus-inference-query"
