"""Pure response-formatting functions for MCP tool output."""

from __future__ import annotations

from .corpus_repository import CorpusSummary, ReloadResult
from .detectors import StandardsCheckResult


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


def format_check_against_standards(result: StandardsCheckResult) -> str:
    """Format standards check result as a markdown violations table."""
    if not result.violations and not result.skipped_rules:
        return "No standards violations detected."

    lines: list[str] = []
    if result.violations:
        lines.append("| Rule | Title | Severity | Snippet | Exemplar |")
        lines.append("|------|-------|----------|---------|----------|")
        for v in result.violations:
            snippet = v.snippet.replace("\n", " ").replace("|", "\\|")
            exemplar = v.exemplar_citation or "none"
            lines.append(f"| {v.rule_id} | {v.rule_title} | {v.severity} | {snippet} | {exemplar} |")
    else:
        lines.append("No violations detected.")

    if result.skipped_rules:
        skipped_str = ", ".join(f"{s.rule_id} ({s.reason_code})" for s in result.skipped_rules)
        lines.append(f"\n**Skipped rules**: {skipped_str}.")

    return "\n".join(lines)
