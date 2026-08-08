#!/bin/sh
# POSIX-compliant local install for macOS/Linux.
# Prefers uv when available; falls back to python3 -m venv + pip.

set -eu

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
venv_dir="${VENV_DIR:-$repo_root/.venv}"

if command -v uv >/dev/null 2>&1; then
  uv venv --allow-existing "$venv_dir"
  uv pip install --python "$venv_dir" -e "$repo_root"
else
  echo "uv not found; falling back to python3 -m venv."
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is not installed. Install Python 3.11+ first." >&2
    exit 1
  fi
  # Reuse an already-active venv if one is set; otherwise create/reuse .venv.
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    venv_dir="$VIRTUAL_ENV"
    echo "Using active virtual environment at $venv_dir"
  elif [ ! -d "$venv_dir" ]; then
    python3 -m venv "$venv_dir"
  fi
  "$venv_dir/bin/python" -m pip install --upgrade pip
  "$venv_dir/bin/python" -m pip install -e "$repo_root"
fi

echo "Installed corpus-inference-query into $venv_dir"
echo "CLI available at $venv_dir/bin/corpus-inference-query"
