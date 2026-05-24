# corpus-inference-query MCP Server

MCP server that indexes a **writing corpus** — reference works, exemplars by genre, and personal writings — and exposes citation lookup, natural-language search, style/type filtering, standards-violation detection, and Jungian concept analysis with optional local inference via Ollama.

## Quick Start

```bash
# Install into a local venv (for development)
bash scripts/install_local.sh

# Or install globally (for Claude Code / Claude Desktop)
uv tool install /path/to/corpus-inference-query
```

### With inference extras (Ollama + settings)

```bash
# Local venv
.venv/bin/pip install -e ".[all]"

# Global
uv tool install --force /path/to/corpus-inference-query --with openai --with pydantic-settings
```

### With vector search only

```bash
.venv/bin/pip install -e ".[vector]"
```

## Register with Claude Code

Add to `~/.claude/settings.json` under `mcpServers`:

```json
"corpus-inference-query": {
  "type": "stdio",
  "command": "/Users/YOU/.local/bin/corpus-inference-query"
}
```

## Register with Claude Desktop

Add to `~/.claude.json` under `mcpServers`:

```json
"corpus-inference-query": {
  "type": "stdio",
  "command": "/Users/YOU/.local/bin/corpus-inference-query"
}
```

To override the corpus path in either config, add an `env` block:

```json
"corpus-inference-query": {
  "type": "stdio",
  "command": "/Users/YOU/.local/bin/corpus-inference-query",
  "env": {
    "CORPUS_INFERENCE_PATH": "/path/to/your/writing-corpus"
  }
}
```

Or run the registration script (handles both):

```bash
python scripts/register_mcp.py              # Claude Desktop only
python scripts/register_mcp.py --claude-code # Claude Desktop + Claude Code
```

Restart Claude Code / Claude Desktop after registering.

## Corpus Setup

The server reads from `~/Documents/writing-corpus/` by default. The directory needs a `corpus.toml` manifest:

```toml
[[source]]
shorthand = "Jung-PU"
id = "jung-psychology-unconscious"
path = "references/jung-psychology-unconscious/"
title = "Psychology of the Unconscious"
author = "Carl Jung"
year = 1916
default_style = ["analytical"]
default_type = ["psychology", "essay"]
chunking_strategy = "paragraph_group"

[[source]]
shorthand = "HTWS"
path = "references/fish-howtowriteasentence/"
title = "How to Write a Sentence"
author = "Stanley Fish"
year = 2011
default_style = ["subordinating", "additive"]
default_type = ["essay", "book"]
```

Each `[[source]]` points to a directory of `.md` files under the corpus root.

## Environment Variables

All prefixed with `CORPUS_INFERENCE_`:

| Variable | Default | Purpose |
|---|---|---|
| `PATH` | `~/Documents/writing-corpus` | Corpus directory |
| `CACHE_PATH` | `~/.cache/corpus-inference-query/lance` | Vector index cache |
| `EMBED_MODEL` | `BAAI/bge-base-en-v1.5` | fastembed model for vector search |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `olmo3.1:32b` | Local inference model |
| `CHUNK_TARGET_TOKENS` | `512` | Chunker target size |
| `CHUNK_MAX_TOKENS` | `1024` | Chunker max size |
| `CHUNK_OVERLAP_TOKENS` | `64` | Chunk overlap |

## MCP Tools

### Corpus tools
| Tool | Purpose |
|---|---|
| `list_corpora` | List all corpora with metadata and section counts |
| `query` | Search by citation or natural language with style/type/corpus filters |
| `lookup_citation` | Resolve a shorthand citation (e.g. `HTWS §Subordinating`) |
| `find_exemplars` | Find exemplar passages by style, type, and length |
| `find_similar_voice` | Find passages with voice similar to provided text |
| `suggest_opening` | Suggest opening sentences for a writing type |
| `suggest_rewrite` | Find exemplars in a target style, ranked by length match |
| `check_against_standards` | Check writing against standards (§1-§15 + §A-§J) |
| `reload` | Reload the corpus index from disk |

### Jungian concept tools
| Tool | Purpose |
|---|---|
| `explore_concept` | Search for passages related to a Jungian concept |
| `analyze_with_concept` | Analyze text through a Jungian lens using Ollama inference |
| `concept_connections` | Find passages discussing two concepts together |

Supported concepts: `individuation`, `shadow`, `anima_animus`, `dream_work`, `collective_unconscious`, `archetypes`, `persona_mask`, `self_realization`, `synchronicity`, `active_imagination`.

## Repository Layout

```
src/corpus_inference_query/
  server.py            MCP server entry point (12 tools)
  corpus_config.py     corpus manifest and shorthand definitions
  corpus_repository.py facade over indexer, search, and vector store
  indexer.py           corpus loading, chunking, and section indexing
  search.py            citation parsing and search formatting
  vector_store.py      optional vector search (requires [vector] extras)
  chunker.py           paragraph-group chunking for dense prose
  concepts.py          Jungian concept vocabulary and keyword expansion
  ollama_facade.py     Ollama inference via OpenAI-compatible API
  settings.py          centralized config via pydantic-settings
  detectors/           standards-rule detection (§1-§15, §A-§J)
  tag_filter.py        style/type tag filtering
  tool_responses.py    MCP response formatting
standards/
  writing-standards.md writing standards §1-§15 and §A-§J
scripts/
  install_local.sh     create local venv and install
  register_mcp.py      register MCP with Claude Desktop / Claude Code
  build_dist.sh        build wheel and sdist
  test.sh              run test suite
tests/
  fixtures/corpus/     fixture corpus (HTWS, Strunk, Jung-PU)
docs/superpowers/
  specs/               design spec
  plans/               implementation plans per milestone
```

## Run Tests

```bash
bash scripts/test.sh
# or directly
python -m pytest -q
```

## Design Docs

Architecture and milestone plan: `docs/superpowers/specs/2026-05-22-corpus-inference-query-design.md`
