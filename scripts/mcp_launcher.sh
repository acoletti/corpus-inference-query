#!/bin/sh
# MCP launcher: export .env.local into the environment, then exec the server.
# Registered MCP clients invoke this instead of the venv binary directly so
# corpus path / cache settings live in one editable file.
set -eu

ROOT="${CORPUS_INFERENCE_PROJECT_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

if [ -f "$ROOT/.env.local" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$ROOT/.env.local"
    set +a
fi

exec "$ROOT/.venv/bin/corpus-inference-query" "$@"
