"""Pure response-formatting functions for MCP tool output."""

from __future__ import annotations

import json
from dataclasses import asdict

from .corpus_repository import CorpusSummary, ReloadResult
from .detectors import StandardsCheckResult
from .flow import FlowCheckResult
from .meter import MeterCheckResult


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


def format_check_meter_json(result: MeterCheckResult) -> str:
    """Format meter check result as a machine-readable JSON object.

    Off-meter lines are listed individually; conforming lines are summarized
    by count to keep the payload small for blackboard storage.
    """
    off_meter = [
        {
            "line_number": s.line_number,
            "text": s.text,
            "syllables": s.syllables,
            "expected": s.expected,
            "deviation": s.deviation,
        }
        for s in result.lines
        if abs(s.deviation) > result.tolerance
    ]
    payload = {
        "status": "conforming" if not off_meter else "deviations",
        "meter": result.meter,
        "expected_syllables": result.expected_syllables,
        "tolerance": result.tolerance,
        "line_count": result.line_count,
        "conforming_count": result.conforming_count,
        "conformity_ratio": round(result.conformity_ratio, 3),
        "off_meter_lines": off_meter,
        "note": (
            "Syllable-count check only (vowel-group approximation); stress "
            "placement (iamb vs. trochee) is not verified."
        ),
    }
    return json.dumps(payload, indent=2)


def format_check_meter(result: MeterCheckResult) -> str:
    """Format meter check result as a markdown scan table."""
    if result.line_count == 0:
        return "No verse lines found to scan."
    header = (
        f"**Meter**: {result.meter} (expected {result.expected_syllables} "
        f"syllables/line, tolerance ±{result.tolerance})\n"
        f"**Conformity**: {result.conforming_count}/{result.line_count} lines "
        f"({result.conformity_ratio:.0%})\n"
    )
    off_meter = [s for s in result.lines if abs(s.deviation) > result.tolerance]
    if not off_meter:
        return header + "\nAll lines conform. Note: syllable-count check only — stress placement is not verified."
    lines = [
        header,
        "| Line | Syllables | Expected | Text |",
        "|------|-----------|----------|------|",
    ]
    for s in off_meter:
        text = s.text.replace("|", "\\|")
        lines.append(f"| {s.line_number} | {s.syllables} ({s.deviation:+d}) | {s.expected} | {text} |")
    lines.append("\nNote: syllable-count check only — stress placement is not verified.")
    return "\n".join(lines)


def format_check_flow_json(result: FlowCheckResult) -> str:
    """Format flow check result as a machine-readable JSON object.

    Designed for orchestrators that store the scan as a blackboard artifact
    and feed findings into a cadence repair loop.
    """
    payload = {
        "status": result.status,
        "unit": result.unit,
        "unit_count": result.unit_count,
        "top_opener": result.top_opener,
        "top_opener_ratio": result.top_opener_ratio,
        "longest_opener_run": result.longest_opener_run,
        "length_cv": result.length_cv,
        "findings": [asdict(f) for f in result.findings],
        "note": (
            "Deterministic repetition census only — whether a repetition is "
            "compulsion or ceremony is the cadence reviewer's judgment."
        ),
    }
    return json.dumps(payload, indent=2)


def format_check_flow(result: FlowCheckResult) -> str:
    """Format flow check result as a markdown findings table."""
    if result.unit_count == 0:
        return "No units found to scan."
    header = (
        f"**Flow scan**: {result.unit_count} {result.unit} | "
        f"top opener '{result.top_opener}' ({result.top_opener_ratio:.0%}) | "
        f"longest opener run {result.longest_opener_run} | "
        f"length CV {result.length_cv:.2f}\n"
    )
    if not result.findings:
        return header + "\nNo monotony markers detected. Note: repetition census only — cadence judgment stays with the reviewer."
    lines = [
        header,
        "| Category | Detail | Evidence |",
        "|----------|--------|----------|",
    ]
    for f in result.findings:
        evidence = f.evidence.replace("|", "\\|")
        lines.append(f"| {f.category} | {f.detail} | {evidence} |")
    lines.append("\nNote: repetition census only — cadence judgment stays with the reviewer.")
    return "\n".join(lines)


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


def format_validate_boundary(payload: str, boundary: str, models: dict) -> str:
    """Validate a JSON payload against a named boundary model; return JSON verdict.

    Success: {"status": "valid", "boundary": ..., "artifact": {...}, "flags": {...}}.
    Failure: {"status": "invalid", "errors": [{loc, msg, type}, ...]} suitable
    for an orchestrator repair-and-retry loop.
    """
    from pydantic import ValidationError

    model = models.get(boundary)
    if model is None:
        return json.dumps({
            "status": "invalid",
            "errors": [{
                "loc": ["boundary"],
                "msg": f"unknown boundary '{boundary}'; expected one of {sorted(models)}",
                "type": "value_error",
            }],
        }, indent=2)
    try:
        data = json.loads(payload)
    except ValueError as exc:
        return json.dumps({
            "status": "invalid",
            "errors": [{"loc": ["payload"], "msg": f"not valid JSON: {exc}", "type": "json_error"}],
        }, indent=2)
    try:
        artifact = model.model_validate(data)
    except ValidationError as exc:
        return json.dumps({
            "status": "invalid",
            "errors": [
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                for e in exc.errors()
            ],
        }, indent=2)

    flags: dict = {}
    scorecard = artifact if boundary == "scorecard" else getattr(artifact, "scorecard", None)
    if scorecard is not None:
        flags["over_smoothing_signature"] = scorecard.over_smoothing_signature()
    if hasattr(artifact, "high_ai_likelihood"):
        flags["high_ai_likelihood"] = artifact.high_ai_likelihood()
    if hasattr(artifact, "flatline_signature"):
        flags["flatline_signature"] = artifact.flatline_signature()
    return json.dumps({
        "status": "valid",
        "boundary": boundary,
        "artifact": artifact.model_dump(),
        "flags": flags,
    }, indent=2)
