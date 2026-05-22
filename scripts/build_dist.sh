#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure uv is available
if ! command -v uv &> /dev/null; then
  echo "uv is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv build "$repo_root"

echo "Built distribution artifacts in $repo_root/dist"
