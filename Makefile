# corpus-inference-query — setup, ingestion, and MCP registration.
# Pattern follows ~/ws/sec-skills: doctor -> init-env -> deps -> ingest -> install-mcp.

ROOT := $(shell pwd)
MCP_NAME := corpus-inference-query
MCP_LAUNCHER := $(ROOT)/scripts/mcp_launcher.sh
MCP_BIN := $(ROOT)/.venv/bin/corpus-inference-query
CORPUS ?= $(CORPUS_INFERENCE_PATH)

.PHONY: setup doctor init-env deps ingest ingest-default dry-run install-mcp \
	install-claude-mcp install-auggie-mcp install-hermes-mcp uninstall-hermes-mcp \
	uninstall-mcp test test-hermes lint clean-cache

HERMES_PYTHON ?= $(HOME)/.hermes/hermes-agent/venv/bin/python

## Full idempotent bootstrap: preflight -> env seed -> deps -> MCP registration -> ingest bundled corpus.
## Swap in your own corpus later with: make ingest CORPUS=/path/to/corpus
setup: doctor init-env deps install-mcp ingest-default
	@echo "setup complete — bundled corpus/ is ready to query"

## Ingest the bundled default corpus (corpus/) so the server works out of the box.
ingest-default: $(MCP_BIN)
	$(MCP_BIN) ingest "$(ROOT)/corpus"

## Preflight: verify required tooling before anything mutates state.
doctor:
	@ok=1; \
	for tool in uv python3; do \
		if command -v $$tool >/dev/null 2>&1; then echo "  [ok] $$tool"; \
		else echo "  [MISSING] $$tool"; ok=0; fi; \
	done; \
	for tool in claude auggie; do \
		if command -v $$tool >/dev/null 2>&1; then echo "  [ok] $$tool (MCP client)"; \
		else echo "  [warn] $$tool not found — install-mcp will skip it"; fi; \
	done; \
	if [ $$ok -eq 1 ]; then echo "doctor: all checks passed"; \
	else echo "doctor: unresolved issues (see above)"; exit 1; fi

## Seed .env.local from .env.example. Never overwrites an existing .env.local.
init-env:
	@if [ -f .env.local ]; then \
		echo ".env.local already exists — leaving untouched"; \
	else \
		cp .env.example .env.local; \
		echo "seeded .env.local — set CORPUS_INFERENCE_PATH inside it"; \
	fi

## Create the venv and install the package with vector extras (local embeddings).
deps:
	uv venv --allow-existing .venv
	uv pip install --python .venv -e ".[vector]"

$(MCP_BIN):
	$(MAKE) deps

## Ingest a corpus directory: chunk, cache, embed. CORPUS=/path or .env.local.
ingest: $(MCP_BIN)
	@if [ -z "$(CORPUS)" ]; then \
		echo "usage: make ingest CORPUS=/path/to/corpus  (or set CORPUS_INFERENCE_PATH in .env.local)"; \
		exit 1; \
	fi
	$(MCP_BIN) ingest "$(CORPUS)"

## Preview chunking without writing the cache or embedding.
dry-run: $(MCP_BIN)
	@test -n "$(CORPUS)" || { echo "usage: make dry-run CORPUS=/path/to/corpus"; exit 1; }
	$(MCP_BIN) ingest "$(CORPUS)" --dry-run

## Register the launcher with every detected MCP client.
install-mcp: $(MCP_BIN) install-claude-mcp install-auggie-mcp install-hermes-mcp

install-claude-mcp:
	@if command -v claude >/dev/null 2>&1; then \
		claude mcp remove $(MCP_NAME) --scope user 2>/dev/null || true; \
		claude mcp add --scope user $(MCP_NAME) -- $(MCP_LAUNCHER); \
		claude mcp get $(MCP_NAME); \
	else echo "claude CLI not found — skipping"; fi

install-auggie-mcp:
	@if command -v auggie >/dev/null 2>&1; then \
		auggie mcp add $(MCP_NAME) --replace --command $(MCP_LAUNCHER); \
		auggie mcp list | grep $(MCP_NAME); \
	else echo "auggie CLI not found — skipping"; fi

## Register with Hermes Agent. Hermes has no `mcp add` CLI, so this edits
## ~/.hermes/config.yaml directly (backed up, atomic, verified). Skips
## cleanly when Hermes is not installed. Restart Hermes to pick it up.
install-hermes-mcp:
	@if [ -f "$(HOME)/.hermes/config.yaml" ]; then \
		if [ -x "$(HERMES_PYTHON)" ]; then PY="$(HERMES_PYTHON)"; else PY=python3; fi; \
		"$$PY" ./scripts/hermes_add.py --name $(MCP_NAME) --command $(MCP_LAUNCHER); \
	else echo "Hermes Agent not found (~/.hermes/config.yaml) — skipping"; fi

uninstall-hermes-mcp:
	@if [ -f "$(HOME)/.hermes/config.yaml" ]; then \
		if [ -x "$(HERMES_PYTHON)" ]; then PY="$(HERMES_PYTHON)"; else PY=python3; fi; \
		"$$PY" ./scripts/hermes_add.py --name $(MCP_NAME) --remove; \
	else echo "Hermes Agent not found — skipping"; fi

## Regression tests for the Hermes registrar (uses throwaway config copies).
test-hermes:
	./scripts/test_hermes_add.sh

uninstall-mcp:
	-command -v claude >/dev/null 2>&1 && claude mcp remove $(MCP_NAME) --scope user 2>/dev/null || true
	-command -v auggie >/dev/null 2>&1 && auggie mcp remove $(MCP_NAME) 2>/dev/null || true

test:
	uv run --extra dev python -m pytest tests/ -q

lint:
	uvx ruff check src tests --line-length 88

## Remove ingest + embedding caches (forces full re-ingest on next run).
clean-cache:
	rm -rf ~/.cache/corpus-inference-query
