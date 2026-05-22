"""Detector registry: maps §-id → function; exposes run_all()."""
from __future__ import annotations

from .base import DetectorFn, Violation
from . import rules as _r

_TYPE_TO_ANNEX: dict[str, str] = {
    "article": "§A",
    "longform-journalism": "§A",
    "email": "§B",
    "letter": "§C",
    "cover-letter": "§C",
    "technical-doc": "§D",
    "rfc": "§D",
    "readme": "§D",
    "runbook": "§D",
    "api-doc": "§D",
    "newsletter": "§E",
    "op-ed": "§F",
    "blog-post": "§G",
    "regular-blog": "§G",
    "white-paper": "§H",
    "memo": "§I",
    "speech": "§J",
    "talk-transcript": "§J",
}

UNIVERSAL_DETECTORS: dict[str, tuple[str, DetectorFn]] = {
    "§1": ("Clarity", _r.detect_clarity),
    "§2": ("Cohesion", _r.detect_cohesion),
    "§3": ("Concision", _r.detect_concision),
    "§4": ("Voice and Agency", _r.detect_voice_agency),
    "§5": ("Diction and Register", _r.detect_diction_register),
    "§6": ("Sentence Rhythm", _r.detect_sentence_rhythm),
    "§7": ("Audience Fit", _r.detect_audience_fit),
    "§8": ("Argument Honesty", _r.detect_argument_honesty),
    "§9": ("Opening Craft", _r.detect_opening_craft),
    "§10": ("Closing Craft", _r.detect_closing_craft),
    "§11": ("Concrete Over Abstract", _r.detect_concrete_abstract),
    "§12": ("Style Consciousness", _r.detect_style_consciousness),
    "§13": ("Voice Fidelity", _r.detect_voice_fidelity),
    "§14": ("Transitions", _r.detect_transitions),
    "§15": ("Lede and Title Craft", _r.detect_lede_and_title),
}

TYPE_DETECTORS: dict[str, tuple[str, DetectorFn]] = {
    "§A": ("Article", _r.detect_article),
    "§B": ("Email", _r.detect_email),
    "§C": ("Letter", _r.detect_letter),
    "§D": ("Technical Doc", _r.detect_technical_doc),
    "§E": ("Newsletter", _r.detect_newsletter),
    "§F": ("Op-Ed", _r.detect_op_ed),
    "§G": ("Blog Post", _r.detect_blog_post),
    "§H": ("White Paper", _r.detect_white_paper),
    "§I": ("Memo", _r.detect_memo),
    "§J": ("Speech", _r.detect_speech),
}

_SKIP_REASONS: dict[str, str] = {
    "§13": "personal_corpus_empty",
    "§7": "type_unknown",
}


def run_all(text: str, types: list[str] | None = None) -> dict:
    """Run all applicable detectors; return {violations, skipped_rules, types_used}."""
    violations: list[dict] = []
    skipped: list[dict] = []

    for rule_id, (title, fn) in UNIVERSAL_DETECTORS.items():
        if rule_id == "§7" and not types:
            skipped.append({"rule_id": rule_id, "rule_title": title, "reason": "type_unknown"})
            continue
        result = fn(text, types)
        if result is None:
            reason = _SKIP_REASONS.get(rule_id, "not_applicable")
            skipped.append({"rule_id": rule_id, "rule_title": title, "reason": reason})
        else:
            violations.extend(_violation_to_dict(v) for v in result)

    applicable_annexes: set[str] = set()
    if types:
        for t in types:
            annex = _TYPE_TO_ANNEX.get(t)
            if annex:
                applicable_annexes.add(annex)

    for annex_id in sorted(applicable_annexes):
        title, fn = TYPE_DETECTORS[annex_id]
        result = fn(text, types)
        if result is None:
            skipped.append({"rule_id": annex_id, "rule_title": title, "reason": "not_applicable"})
        else:
            violations.extend(_violation_to_dict(v) for v in result)

    return {
        "violations": violations,
        "skipped_rules": skipped,
        "types_used": types or [],
    }


def _violation_to_dict(v: Violation) -> dict:
    return {
        "rule_id": v.rule_id,
        "rule_title": v.rule_title,
        "severity": v.severity,
        "snippet": v.snippet,
        "span": list(v.span) if v.span else None,
        "exemplar_citation": v.exemplar_citation,
        "suggested_rewrite_from_exemplar": v.suggested_rewrite_from_exemplar,
    }
