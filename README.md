# corpus-inference-query MCP Server

`corpus-inference-query` is a Python MCP server that indexes a **writing corpus** — reference works, exemplars by genre, and the user's personal writings — and returns relevant excerpts by shorthand citation, natural-language query, style/type filter, or standards-violation check.

## What This Repo Provides

- A stdio MCP server entry point: `corpus-inference-query`
- A lightweight local indexer over a writing-corpus directory
- Citation lookup for shorthands like `HTWS §Subordinating`
- Natural-language search across configured corpora
- Mechanical standards-violation detection (`check_against_standards`) against `standards/writing-standards.md`
- Exemplar retrieval and drafting aids (`find_exemplars`, `find_similar_voice`, `suggest_opening`, `suggest_rewrite`)

## Repository Layout

```text
src/corpus_inference_query/
  server.py          MCP server entry point
  corpus_config.py   corpus manifest and shorthand definitions
  indexer.py         corpus loading and section indexing
  search.py          citation parsing and search formatting
  vector_store.py    optional vector search backend (requires [vector] extras)
standards/
  writing-standards.md   §1-§15 universal rules, §A-§J type addenda, Annex X (M3)
scripts/
  install_local.sh   create a local venv and install the package
  build_dist.sh      build wheel and sdist artifacts
  test.sh            run the lightweight unit test suite
  register_mcp.py    register the MCP into a Claude/Codex config
tests/
  test_search.py     search smoke tests (includes vector store tests)
  test_server.py     MCP tool routing tests
  fixtures/corpus/   tiny writing-corpus fixture used by tests
docs/superpowers/
  specs/             design specs (the authoritative architecture document)
  plans/             implementation plans per milestone
```

## Prerequisites

- Python 3.11+
- A writing corpus directory at `CORPUS_INFERENCE_PATH` (default `~/Documents/writing-corpus`)

## Quick Start

```bash
cd /path/to/corpus-inference-query
bash ./scripts/install_local.sh
./.venv/bin/corpus-inference-query --help
```

### Vector Search Extras (optional)

```bash
./.venv/bin/pip install -e ".[vector]"
```

Embeds the corpus on first NL query (~5–10s) and caches the index at `~/.cache/corpus-inference-query/lance/`. Cache is invalidated automatically when the corpus changes.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CORPUS_INFERENCE_PATH` | `~/Documents/writing-corpus` | Path to the writing corpus directory |
| `CORPUS_INFERENCE_CACHE_PATH` | `~/.cache/corpus-inference-query/lance` | Where the vector index is cached |
| `CORPUS_INFERENCE_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model name for vector search |

## MCP Configuration

```json
{
  "mcpServers": {
    "corpus-inference-query": {
      "type": "stdio",
      "command": "/absolute/path/to/.venv/bin/corpus-inference-query",
      "env": {
        "CORPUS_INFERENCE_PATH": "/absolute/path/to/writing-corpus"
      }
    }
  }
}
```

## Query Examples (M1 scope — limited)

| Query | Returns |
|---|---|
| `HTWS §Subordinating` | Fish, Subordinating chapter (fixture stub) |
| `Strunk §Omit Needless Words` | Strunk and White (fixture stub) |

Standards checking, exemplar retrieval, and drafting aids (M2-M3) are documented in `standards/writing-standards.md`. Gutenberg-seeded real corpora and the `/writing` skill arrive in milestones M4-M6.

## Run Tests

```bash
bash ./scripts/test.sh
```

## Design Docs

The architecture and milestone plan live in `docs/superpowers/specs/` and `docs/superpowers/plans/`. Start with the design spec for any deeper work.
