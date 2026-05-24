"""MCP stdio server for writing corpus queries."""
from __future__ import annotations
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .corpus_repository import CorpusRepository
from .tool_responses import format_check_results, format_list_corpora, format_reload

logger = logging.getLogger(__name__)

_DEFAULT_CORPUS_PATH = os.path.expanduser("~/Documents/writing-corpus")
CORPUS_PATH = Path(os.path.expanduser(os.environ.get("CORPUS_INFERENCE_PATH", _DEFAULT_CORPUS_PATH)))

mcp = FastMCP("corpus-inference-query")

_CHARS_PER_TOKEN = 4
_MAX_TOKENS_CEILING = 4000
_TOP_K_CEILING = 20

_repo: CorpusRepository | None = None


def _get_repo() -> CorpusRepository:
    global _repo
    if _repo is None:
        _repo = CorpusRepository(CORPUS_PATH)
    return _repo


@mcp.tool()
def query(query: str, max_tokens: int = 1500, top_k: int = 3, style: list[str] | None = None, type_filter: list[str] | None = None, corpus: str | None = None) -> str:
    """Query the writing corpus by shorthand citation or natural language, with optional style/type/corpus filters.

    Args:
        query: Citation (e.g. "HTWS §Subordinating") or natural language.
        max_tokens: Target response size in tokens (approx). Default 1500, max 4000.
        top_k: Number of sections to return. Default 3, max 20.
        style: Style tags to filter by (AND semantics, e.g. ["subordinating"]).
        type_filter: Type tags to filter by (AND semantics, e.g. ["essay"]).
        corpus: Corpus shorthand to restrict to (e.g. "HTWS").
    """
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    top_k = max(1, min(top_k, _TOP_K_CEILING))
    return _get_repo().search(query, top_k=top_k, style=style, type_filter=type_filter, corpus=corpus, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def list_corpora() -> str:
    """List all available corpora with metadata, style/type tags, and section counts."""
    return format_list_corpora(_get_repo().list_corpora())


@mcp.tool()
def lookup_citation(citation: str, max_tokens: int = 1500) -> str:
    """Resolve a shorthand citation to its full section text (e.g. "HTWS §Subordinating").

    Args:
        citation: Shorthand citation string.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    return _get_repo().lookup_citation(citation, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def find_exemplars(style: list[str] | None = None, type_filter: list[str] | None = None, length: str | None = None, top_k: int = 5, max_tokens: int = 1500) -> str:
    """Find exemplar writing passages filtered by style tags, type tags, and length.

    Args:
        style: Style tags to match (e.g. ["subordinating"]).
        type_filter: Type tags to match (e.g. ["essay"]).
        length: Length bucket: "short" (<500 chars), "medium" (500-2000), "long" (>2000).
        top_k: Number of results. Default 5, max 20.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    return _get_repo().find_exemplars(style=style, type_filter=type_filter, length=length, top_k=top_k, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def check_against_standards(text: str, types: list[str] | None = None) -> str:
    """Check writing against standards and return violations with rule citations.

    Args:
        text: Writing to check.
        types: Writing type context (e.g. ["essay"]).
    """
    return format_check_results(_get_repo().check_against_standards(text, types))


@mcp.tool()
def find_similar_voice(text: str, corpus: str = "personal", top_k: int = 5, max_tokens: int = 1500) -> str:
    """Find corpus passages with voice similar to provided text.

    Args:
        text: Text to match voice against.
        corpus: Corpus shorthand to search within. Default "personal".
        top_k: Number of results. Default 5, max 20.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    return _get_repo().find_similar_voice(text, top_k=top_k, corpus=corpus, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def suggest_opening(type_name: str, style: list[str] | None = None, topic: str | None = None, top_k: int = 5, max_tokens: int = 1500) -> str:
    """Suggest opening sentences from the corpus for a given writing type and style.

    Args:
        type_name: Writing type (e.g. "essay", "email", "book").
        style: Style tags to filter by.
        topic: Optional topic hint to rank results.
        top_k: Number of results. Default 5, max 20.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    return _get_repo().suggest_opening(type_name, style=style, topic=topic, top_k=top_k, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def suggest_rewrite(text: str, target_style: str, top_k: int = 5, max_tokens: int = 1500) -> str:
    """Return exemplar passages in a target style, ranked by similar length to the input text.

    Args:
        text: Text you want to rewrite (used for length matching).
        target_style: Style tag to match (e.g. "subordinating", "additive").
        top_k: Number of results. Default 5, max 20.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    return _get_repo().suggest_rewrite(text, target_style, top_k=top_k, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def explore_concept(concept: str, corpus: str | None = None, top_k: int = 5, max_tokens: int = 1500) -> str:
    """Search the corpus for passages related to a Jungian concept.

    Args:
        concept: Jungian concept name (e.g. "shadow", "individuation", "dream_work").
        corpus: Corpus shorthand to restrict to.
        top_k: Number of results. Default 5, max 20.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    from .concepts import concept_search_query  # noqa: PLC0415

    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    query_text = concept_search_query(concept)
    return _get_repo().search(query_text, top_k=top_k, corpus=corpus, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def analyze_with_concept(text: str, concept: str, max_tokens: int = 1500) -> str:
    """Analyze text through the lens of a Jungian concept using local inference.

    Args:
        text: Text to analyze.
        concept: Jungian concept to apply (e.g. "shadow", "individuation").
        max_tokens: Target response size. Default 1500, max 4000.
    """
    from .concepts import concept_search_query  # noqa: PLC0415
    from .ollama_facade import get_facade  # noqa: PLC0415

    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    query_text = concept_search_query(concept)
    context = _get_repo().search(query_text, top_k=3, max_chars=2000 * _CHARS_PER_TOKEN)
    facade = get_facade()
    if facade is None:
        return f"[inference unavailable — showing retrieval results]\n\n{context}"
    system = f"You are a Jungian psychology expert. Analyze the user's text through the concept of '{concept}'. Ground your analysis in the provided corpus excerpts."
    user_msg = f"Corpus context:\n{context}\n\nText to analyze:\n{text}"
    result = facade.complete(system, user_msg)
    return result if result else f"[inference failed — showing retrieval results]\n\n{context}"


@mcp.tool()
def concept_connections(concept_a: str, concept_b: str, top_k: int = 3, max_tokens: int = 1500) -> str:
    """Find passages that discuss two Jungian concepts together.

    Args:
        concept_a: First concept (e.g. "shadow").
        concept_b: Second concept (e.g. "individuation").
        top_k: Number of results. Default 3, max 20.
        max_tokens: Target response size. Default 1500, max 4000.
    """
    from .concepts import concept_search_query  # noqa: PLC0415

    top_k = max(1, min(top_k, _TOP_K_CEILING))
    max_tokens = max(1, min(max_tokens, _MAX_TOKENS_CEILING))
    q_a = concept_search_query(concept_a)
    q_b = concept_search_query(concept_b)
    combined = f"{q_a} {q_b}"
    return _get_repo().search(combined, top_k=top_k, max_chars=max_tokens * _CHARS_PER_TOKEN)


@mcp.tool()
def reload() -> str:
    """Reload the corpus index from disk. Use after editing corpus files."""
    global _repo
    _repo = None
    result = _get_repo().reload()
    return format_reload(result)


def main():
    try:
        _get_repo()._get_vector_store()
    except Exception:
        logger.warning("Startup warmup failed; index will be built on first query", exc_info=True)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
