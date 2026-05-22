"""Pure response-formatting functions for MCP tool output."""

from __future__ import annotations

from typing import Any

from .corpus_repository import CorpusSummary, ReloadResult


def format_list_corpora(summaries: list[CorpusSummary]) -> str:
    """Format corpus list as markdown table with totals."""
    if not summaries:
        return "No corpora configured."
    lines = [
        "| Shorthand | Title | Author | Style Tags | Type Tags | Sections |",
        "|-----------|-------|--------|------------|-----------|---------|",
    ]
    total_sections = 0
    for s in summaries:
        style_str = ", ".join(s.default_style) if s.default_style else "none"
        type_str = ", ".join(s.default_type) if s.default_type else "none"
        lines.append(
            f"| {s.shorthand} | {s.title} | {s.author} | {style_str} | {type_str} | {s.doc_count} |"
        )
        total_sections += s.doc_count
    lines.append(f"\n**Total**: {len(summaries)} corpora, {total_sections} sections indexed.")
    return "\n".join(lines)


def format_reload(result: ReloadResult) -> str:
    """Format reload result as brief status message."""
    return f"Reloaded {result.doc_count} sections from {result.corpora_count} corpora."


def format_check_stub(result: dict[str, Any]) -> str:
    """Format standards check stub result."""
    types_str = ", ".join(result.get("types_provided", [])) or "none"
    return (
        f"Standards check: not yet implemented (M3).\n"
        f"Text length: {result['text_length']} characters.\n"
        f"Configured types: {types_str}."
    )
