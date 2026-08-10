"""Pure response-formatting functions for MCP tool output."""

from __future__ import annotations

import json
from dataclasses import asdict

from .corpus_repository import CorpusSummary, ReloadResult
from .detectors import StandardsCheckResult


def format_list_corpora(
    summaries: list[CorpusSummary],
    corpus_path: str | None = None,
    vector_index_status: str | None = None,
) -> str:
    """Format corpus list as markdown table with totals and an optional status header."""
    header: list[str] = []
    if corpus_path is not None:
        header.append(f"**Active Corpus Path**: {corpus_path}")
    if vector_index_status is not None:
        header.append(f"**Vector Index Status**: {vector_index_status}")
    if header:
        header.append("")
    if not summaries:
        return "\n".join([*header, "No corpora configured."]) if header else "No corpora configured."
    lines = [
        *header,
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


def format_check_against_standards_json(result: StandardsCheckResult) -> str:
    """Format standards check result as a machine-readable JSON object.

    Designed for orchestrators that store the check result as a blackboard
    artifact and gate on violation counts programmatically.
    """
    payload = {
        "status": "clean" if not result.violations else "violations",
        "violation_count": len(result.violations),
        "violations": [asdict(v) for v in result.violations],
        "skipped_rules": [asdict(s) for s in result.skipped_rules],
    }
    return json.dumps(payload, indent=2)


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
