"""MCP stdio server for writing corpus queries."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .corpus_config import CORPUS_SPECS
from .indexer import Section, build_index
from .search import _format_results, _parse_citation, search
from .vector_store import build_vector_store, vector_search

logger = logging.getLogger(__name__)

# Resolve corpus path from env or default
_DEFAULT_CORPUS_PATH = os.path.expanduser("~/Documents/writing-corpus")
CORPUS_PATH = Path(
    os.path.expanduser(
        os.environ.get("CORPUS_INFERENCE_PATH", _DEFAULT_CORPUS_PATH)
    )
)

mcp = FastMCP("corpus-inference-query")

# Token / character budget constants.
# _CHARS_PER_TOKEN: rough token-to-char ratio used throughout; matches search.py:118.
# _MAX_TOKENS_CEILING: cap for the max_tokens parameter (~16k chars), avoids
#   oversized MCP tool responses and guards against non-positive caller values.
_CHARS_PER_TOKEN = 4
_MAX_TOKENS_CEILING = 4000
_TOP_K_CEILING = 20

# Module-level index — built on first query (lazy)
_index: list[Section] | None = None

# Sentinel distinguishing "not yet tried" (None) from "unavailable" after failure.
_VECTOR_STORE_UNAVAILABLE = object()
_vector_store = None  # None | _VECTOR_STORE_UNAVAILABLE | lancedb.Table


def _get_vector_store():
    """Return the lancedb Table, or None when vector extras are not installed."""
    global _vector_store
    if _vector_store is None:
        try:
            _vector_store = build_vector_store(_get_index())
        except Exception:
            logger.warning(
                "build_vector_store failed; vector search unavailable for this process",
                exc_info=True,
            )
            _vector_store = _VECTOR_STORE_UNAVAILABLE
    if _vector_store is _VECTOR_STORE_UNAVAILABLE:
        return None
    return _vector_store


def _get_index() -> list[Section]:
    global _index
    if _index is None:
        if not CORPUS_PATH.exists():
            raise RuntimeError(
                f"Corpus path does not exist: {CORPUS_PATH}\n"
                f"Set CORPUS_INFERENCE_PATH to the correct location."
            )
        _index = build_index(CORPUS_PATH)
    return _index


def _execute_natural_language_search(index, query, max_chars, top_k):
    """Try vector search; fall back to None so caller can use keyword search."""
    try:
        table = _get_vector_store()
        if table is not None:
            nl_sections = vector_search(table, index, query, top_k)
            if nl_sections:
                return _format_results(nl_sections, max_chars)
    except Exception:
        logger.error(
            "vector_search failed, falling back to keyword search",
            exc_info=True,
        )
    return None


@mcp.tool()
def query(
    query: str,  # named 'query' to match the FastMCP schema field exposed to clients
    max_tokens: int = 1500,
    top_k: int = 3,
) -> str:
    """Query the writing corpus by shorthand citation or natural language.

    Examples:
      - "HTWS §Subordinating" → Fish, How to Write a Sentence, Subordinating chapter
      - "Strunk §Omit Needless Words" → Strunk and White, omit needless words
      - "subordinating sentence dependent clause" → natural language search across all corpora

    Args:
        query: The query string — a shorthand citation (e.g. "HTWS §Subordinating")
               or natural language (e.g. "additive style parataxis").
        max_tokens: Target response size in tokens (approximate). Default 1500, max 4000.
        top_k: Number of sections to return for natural language queries. Default 3, max 20.

    Returns:
        Matching corpus excerpts formatted with citation headers.
    """
    index = _get_index()
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_chars = max_tokens * _CHARS_PER_TOKEN  # compute once; used by both search paths

    # Citation queries (shorthand + §) skip vector search. Note: _parse_citation is
    # called here to route and then called again inside search() — both call sites
    # must stay in sync on what constitutes a valid citation.
    if _parse_citation(query)[0] is not None:
        return search(index, query, max_chars=max_chars, top_k=top_k)

    result = _execute_natural_language_search(index, query, max_chars, top_k)
    if result is not None:
        return result

    return search(index, query, max_chars=max_chars, top_k=top_k)


@mcp.tool()
def list_corpora() -> str:
    """List all available corpora, their shorthands, and example citations.

    Returns:
        A formatted table of corpus IDs, shorthands, section counts, and
        up to 3 example citations per corpus to aid query construction.
    """
    index = _get_index()
    lines = [
        "| Shorthand | Corpus | Sections | Example citations |",
        "|-----------|--------|----------|-------------------|",
    ]
    for spec in CORPUS_SPECS:
        corpus_sections = [s for s in index if s.shorthand == spec.shorthand]
        count = len(corpus_sections)
        examples = ", ".join(f"`{s.citation}`" for s in corpus_sections[:3])
        lines.append(f"| `{spec.shorthand}` | {spec.description} | {count} | {examples} |")
    lines.append(f"\n**Total sections indexed**: {len(index)}")
    lines.append(f"**Corpus path**: `{CORPUS_PATH}`")
    return "\n".join(lines)


@mcp.tool()
def reload() -> str:
    """Reload the corpus index and vector store from disk.

    Use after editing corpus files to pick up changes without restarting
    the MCP server process. The vector store is cleared and will be rebuilt
    lazily on the next natural-language query.

    Returns:
        A summary confirming the section count after reload.
    """
    global _index, _vector_store
    _index = None
    _vector_store = None  # reset sentinel so next NL query rebuilds the store
    index = _get_index()
    return f"Reloaded {len(index)} sections from `{CORPUS_PATH}`."


def main():
    # Warm up index and vector store at startup so the first query doesn't pay
    # the build latency. Corpus-missing errors are caught and logged; the server
    # starts regardless and will surface a clear error on the first query.
    try:
        _get_vector_store()
    except Exception:
        logger.warning(
            "Startup warmup failed; index will be built on first query",
            exc_info=True,
        )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
