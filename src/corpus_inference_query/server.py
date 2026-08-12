"""MCP stdio server for writing corpus queries."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .corpus_repository import CorpusRepository
from .flow import FLOW_UNITS
from .flow import check_flow as run_flow_check
from .meter import METERS
from .meter import check_meter as run_meter_check
from .tool_responses import (
    format_check_against_standards,
    format_check_against_standards_json,
    format_check_flow,
    format_check_flow_json,
    format_check_meter,
    format_check_meter_json,
    format_list_corpora,
    format_reload,
    format_validate_boundary,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CORPUS_PATH = str(_REPO_ROOT / "corpus")
_CONFIG_DIR = Path.home() / ".config" / "corpus-inference-query"
_CONFIG_PATH = _CONFIG_DIR / "config.json"


def _load_config() -> dict:
    """Load the persisted JSON config, returning {} if absent or malformed."""
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return {}


def _resolve_corpus_path() -> Path:
    """Resolve the corpus path: env var > config file > default fallback."""
    env = os.environ.get("CORPUS_INFERENCE_PATH")
    if env:
        return Path(os.path.expanduser(env))
    configured = _load_config().get("corpus_path")
    if configured:
        return Path(os.path.expanduser(configured))
    return Path(os.path.expanduser(_DEFAULT_CORPUS_PATH))


CORPUS_PATH = _resolve_corpus_path()

mcp = FastMCP("corpus-inference-query")

_CHARS_PER_TOKEN = 4
_MAX_TOKENS_CEILING = 4000
_TOP_K_CEILING = 20

_repo: CorpusRepository | None = None


def _get_repo() -> CorpusRepository:
    global _repo
    if _repo is None:
        if not CORPUS_PATH.is_dir():
            raise RuntimeError(
                f"Corpus path does not exist or is not a directory: {CORPUS_PATH}\n"
                "Fix it by either:\n"
                "  1. Running `corpus-inference-query init` to configure the corpus path, or\n"
                "  2. Setting the CORPUS_INFERENCE_PATH environment variable."
            )
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
    repo = _get_repo()
    return format_list_corpora(
        repo.list_corpora(),
        corpus_path=str(CORPUS_PATH),
        vector_index_status=repo.vector_index_status(),
    )


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
def check_against_standards(text: str, types: list[str] | None = None, format: str = "markdown") -> str:
    """Check writing against the mechanical writing-standards rules.

    Args:
        text: Writing to check.
        types: Writing type context (e.g. ["essay"]). Inferred from text shape if omitted.
        format: Output format: "markdown" (default, human-readable table) or
            "json" (machine-readable object with status, violation_count,
            violations, skipped_rules — for orchestrators storing the result
            as a blackboard artifact).
    """
    result = _get_repo().check_against_standards(text, types)
    if format == "json":
        return format_check_against_standards_json(result)
    return format_check_against_standards(result)


@mcp.tool()
def check_meter(text: str, meter: str = "iambic_pentameter", tolerance: int = 1, format: str = "markdown") -> str:
    """Check verse lines against a named meter's expected syllable count.

    Deterministic line-length scan built on approximate vowel-group syllable
    counting — verifies syllables per line, NOT stress placement (an
    off-stress but 10-syllable line passes). Blank lines, markdown headings,
    and [AUTHOR: ...] placeholder lines are skipped as scaffolding.

    Args:
        text: Verse to scan (one verse line per text line).
        meter: Named meter. One of: iambic_dimeter (4), iambic_trimeter (6),
            iambic_tetrameter (8), iambic_pentameter (10), iambic_hexameter
            (12), trochaic_tetrameter (8), trochaic_octameter (16),
            anapestic_tetrameter (12), dactylic_hexameter (18), common_meter
            (alternating 8/6). Default iambic_pentameter.
        tolerance: Allowed +/- syllable deviation per line. Default 1.
        format: "markdown" (default, scan table) or "json" (machine-readable
            object with status, conformity_ratio, off_meter_lines — for
            orchestrators storing the result as a blackboard artifact).
    """
    try:
        result = run_meter_check(text, meter=meter, tolerance=max(0, tolerance))
    except ValueError as exc:
        if format == "json":
            return json.dumps({"status": "error", "error": str(exc), "known_meters": sorted(METERS)}, indent=2)
        return f"Error: {exc}"
    if format == "json":
        return format_check_meter_json(result)
    return format_check_meter(result)


@mcp.tool()
def check_flow(text: str, unit: str = "auto", format: str = "markdown") -> str:
    """Scan prose or verse for cadence monotony: opener runs, opener dominance,
    repeated phrase scaffolds, and uniform sentence lengths.

    Deterministic repetition census — it counts what repeats and how unit
    lengths vary, and does NOT judge whether a repetition is deliberate
    anaphora or machine flatline (that judgment belongs to the cadence
    reviewer). Blank lines, markdown headings, and [AUTHOR: ...] placeholder
    lines are skipped as scaffolding.

    Args:
        text: Prose or verse to scan.
        unit: Scan unit. "auto" (default) treats the text as verse lines when
            most lines lack terminal punctuation, else prose sentences;
            "lines" and "sentences" force the unit.
        format: "markdown" (default, findings table) or "json"
            (machine-readable object with status, findings — for
            orchestrators storing the result as a blackboard artifact).
    """
    try:
        result = run_flow_check(text, unit=unit)
    except ValueError as exc:
        if format == "json":
            return json.dumps({"status": "error", "error": str(exc), "known_units": list(FLOW_UNITS)}, indent=2)
        return f"Error: {exc}"
    if format == "json":
        return format_check_flow_json(result)
    return format_check_flow(result)


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
def validate_boundary(payload: str, boundary: str = "review") -> str:
    """Validate an LLM-produced editorial artifact against its writing boundary.

    Args:
        payload: JSON string of the artifact (review, debate, or scorecard).
        boundary: Which boundary model to validate against:
            "review" (Phase 2 EditorialReview), "debate" (Phase 3
            DebateResponse), "scorecard" (five-dimension Scorecard),
            "ai_smell", "parataxis_scorecard", "draft", or "cadence"
            (CadenceVerdict — flow level plus per-passage directives).

    Returns a JSON object: {"status": "valid", ...} echoing the normalized
    artifact plus derived flags (e.g. over_smoothing_signature for
    scorecards), or {"status": "invalid", "errors": [...]} with per-field
    Pydantic error locations for repair-and-retry loops.
    """
    from .boundaries import BOUNDARY_MODELS  # noqa: PLC0415

    return format_validate_boundary(payload, boundary, BOUNDARY_MODELS)


@mcp.tool()
def reload() -> str:
    """Reload the corpus index from disk. Use after editing corpus files."""
    global _repo
    _repo = None
    result = _get_repo().reload()
    return format_reload(result)


def _persist_corpus_path(corpus_dir: Path) -> None:
    config = _load_config()
    config["corpus_path"] = str(corpus_dir)
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Saved corpus_path={corpus_dir} to {_CONFIG_PATH}")


def _run_ingest(argv: list[str]) -> int:
    """Ingest a corpus directory and persist it as the active corpus path."""
    from .ingest import main as ingest_main

    rc = ingest_main(argv)
    if rc == 0 and "--dry-run" not in argv and argv and not argv[0].startswith("-"):
        _persist_corpus_path(Path(os.path.expanduser(argv[0])).resolve())
    return rc


def _run_init() -> int:
    """Interactively configure the corpus path, then ingest it."""
    print(f"Current corpus path: {CORPUS_PATH}")
    raw = input("Absolute path to your writing corpus: ").strip()
    if not raw:
        print("No path entered; nothing changed.", file=sys.stderr)
        return 1

    corpus_dir = Path(os.path.expanduser(raw))
    if not corpus_dir.is_dir():
        print(f"Error: {corpus_dir} does not exist or is not a directory.", file=sys.stderr)
        return 1
    return _run_ingest([str(corpus_dir)])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        sys.exit(_run_init())
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        sys.exit(_run_ingest(sys.argv[2:]))
    try:
        _get_repo()._get_vector_store()
    except Exception:
        logger.warning("Startup warmup failed; index will be built on first query", exc_info=True)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
