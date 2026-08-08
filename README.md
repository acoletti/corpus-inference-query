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
  server.py          MCP server entry point (also the `init` / `ingest` CLI)
  ingest.py          ingestion pipeline: walk, chunk, cache, embed
  corpus_config.py   corpus manifest and shorthand definitions
  indexer.py         corpus loading and section indexing
  search.py          citation parsing and search formatting
  vector_store.py    optional vector search backend (requires [vector] extras)
standards/
  writing-standards.md   §1-§15 universal rules, §A-§J type addenda, Annex X (M3)
scripts/
  mcp_launcher.sh    launcher registered with MCP clients (sources .env.local)
  install_local.sh   create a local venv and install the package
  build_dist.sh      build wheel and sdist artifacts
  test.sh            run the lightweight unit test suite
  register_mcp.py    register the MCP into a Claude Desktop/Code config
tests/
  test_ingest.py     ingestion pipeline tests
  test_search.py     search smoke tests (includes vector store tests)
  test_server.py     MCP tool routing tests
  fixtures/corpus/   tiny writing-corpus fixture used by tests
docs/superpowers/
  specs/             design specs (the authoritative architecture document)
  plans/             implementation plans per milestone
```

## Prerequisites

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- A directory of text files — unformatted is fine (`.txt`, `.md`, `.rst`, `.markdown`)
- (Optional) `claude` and/or `auggie` CLIs for automatic MCP registration

## Quick Start

```bash
git clone <repo-url> corpus-inference-query
cd corpus-inference-query
make setup                                    # doctor -> .env.local -> deps -> MCP registration
make ingest CORPUS=/path/to/your/corpus       # chunk, cache, and embed the corpus
```

`make setup` runs preflight checks (`make doctor`), seeds `.env.local` from
`.env.example`, creates `.venv` with the vector extras, and registers
`scripts/mcp_launcher.sh` with every detected MCP client (`claude`, `auggie`).
Restart your MCP client afterwards.

## Ingestion

Point `ingest` at any directory of text files — no manifest or formatting
required. Each top-level subdirectory becomes a corpus shorthand (e.g.
`corpus/CJ/…` → citations like `CJ §dreams.3`):

```bash
make ingest CORPUS=~/personal_dev/docs/corpus    # or: corpus-inference-query ingest <dir>
make dry-run CORPUS=~/personal_dev/docs/corpus   # preview chunking, write nothing
```

The pipeline walks the tree recursively, splits files with a boundary-aware
chunker (1500 chars, 200 overlap — paragraph > sentence > line), caches
sections at `~/.cache/corpus-inference-query/ingest/`, skips unchanged files
by sha256 on re-runs, prunes deleted files, then builds the vector index
eagerly so the first query is fast. Non-text files (PDF, EPUB, JPG) are
ignored. Re-run `make ingest` (or the `reload` MCP tool) after edits.

`ingest <dir>` also persists the directory to
`~/.config/corpus-inference-query/config.json` as the active corpus. At
startup the server resolves the corpus path in this order:

1. `CORPUS_INFERENCE_PATH` environment variable (see `.env.local`)
2. `corpus_path` in `~/.config/corpus-inference-query/config.json`
3. Default fallback: `~/Documents/writing-corpus`

`corpus-inference-query init` remains as an interactive prompt that calls the
same ingestion pipeline. Corpora described by a `corpus.toml` manifest keep
working; the ingest cache takes precedence when present.

## Make Targets

| Target | Purpose |
|---|---|
| `make setup` | Full bootstrap: doctor → init-env → deps → install-mcp |
| `make doctor` | Preflight tool checks (uv, python3, claude, auggie) |
| `make ingest CORPUS=…` | Ingest a corpus directory (chunk + cache + embed) |
| `make dry-run CORPUS=…` | Preview chunking without writing anything |
| `make install-mcp` / `uninstall-mcp` | (De)register with claude + auggie CLIs |
| `make test` / `make lint` | Test suite / ruff |
| `make clean-cache` | Delete ingest + embedding caches |

## Environment Variables

Set these in `.env.local` (sourced by `scripts/mcp_launcher.sh`):

| Variable | Default | Purpose |
|---|---|---|
| `CORPUS_INFERENCE_PATH` | `~/Documents/writing-corpus` | Path to the writing corpus directory |
| `CORPUS_INFERENCE_CACHE_PATH` | `~/.cache/corpus-inference-query/lance` | Where the vector index is cached |
| `CORPUS_INFERENCE_INGEST_CACHE` | `~/.cache/corpus-inference-query/ingest` | Where ingested sections are cached |
| `CORPUS_INFERENCE_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model name for vector search |

## MCP Configuration

`make install-mcp` handles registration. For clients without a CLI, add manually:

```json
{
  "mcpServers": {
    "corpus-inference-query": {
      "type": "stdio",
      "command": "/absolute/path/to/repo/scripts/mcp_launcher.sh"
    }
  }
}
```

The launcher sources `.env.local`, so corpus path and cache settings live in
one file instead of per-client config blocks.

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
