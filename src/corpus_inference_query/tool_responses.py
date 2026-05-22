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


def format_check_results(result: dict[str, Any]) -> str:
    """Format standards check results as markdown."""
    violations = result.get("violations", [])
    skipped = result.get("skipped_rules", [])
    types_used = result.get("types_used", [])

    lines = []

    if types_used:
        lines.append(f"**Types:** {', '.join(types_used)}")

    if not violations:
        lines.append("**Standards check:** No violations found.")
    else:
        lines.append(f"**Standards check:** {len(violations)} violation(s) found.")
        for v in violations:
            severity = v.get("severity", "info").upper()
            rule_id = v.get("rule_id", "?")
            rule_title = v.get("rule_title", "")
            snippet = v.get("snippet", "")
            lines.append(f"\n**{severity}** [{rule_id} {rule_title}]")
            if snippet:
                lines.append(f"> {snippet[:120]}")

    if skipped:
        skipped_ids = ", ".join(s.get("rule_id", "?") for s in skipped)
        lines.append(f"\n*Skipped rules: {skipped_ids}*")

    return "\n".join(lines)
