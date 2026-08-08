"""Maps rule ids to detector functions; resolves which rules apply to a text."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..text_utils import (
    MARKDOWN_HEADING_RE,
    MEMO_HEADER_RE,
    SALUTATION_RE,
    SIGNOFF_RE,
    SUBJECT_LINE_RE,
)
from . import rules
from .types import RuleViolation, SkippedRule, StandardsCheckResult

if TYPE_CHECKING:
    from ..corpus_repository import CorpusRepository

Detector = Callable[[str, "CorpusRepository", list[str]], "RuleViolation | SkippedRule | None"]

# Populated incrementally as rules.py grows (§1-§15).
UNIVERSAL: dict[str, Detector] = {
    "§1": rules.check_s1_clarity,
    "§2": rules.check_s2_cohesion,
    "§3": rules.check_s3_concision,
    "§4": rules.check_s4_voice,
    "§5": rules.check_s5_diction,
    "§6": rules.check_s6_rhythm,
    "§7": rules.check_s7_audience_fit,
    "§8": rules.check_s8_argument_honesty,
    "§9": rules.check_s9_opening,
    "§10": rules.check_s10_closing,
    "§11": rules.check_s11_concrete,
    "§12": rules.check_s12_style_consciousness,
    "§13": rules.check_s13_voice_fidelity,
    "§14": rules.check_s14_transitions,
    "§15": rules.check_s15_lede,
}

# type name -> (rule_id, detector). Populated incrementally (§A-§J).
ADDENDA: dict[str, tuple[str, Detector]] = {
    "article": ("§A", rules.check_a_article),
    "email": ("§B", rules.check_b_email),
    "letter": ("§C", rules.check_c_letter),
    "technical_doc": ("§D", rules.check_d_technical_doc),
    "newsletter": ("§E", rules.check_e_newsletter),
    "op_ed": ("§F", rules.check_f_oped),
    "blog": ("§G", rules.check_g_blog_post),
    "white_paper": ("§H", rules.check_h_white_paper),
    "memo": ("§I", rules.check_i_memo),
    "speech": ("§J", rules.check_j_speech),
}


def infer_types(text: str) -> list[str]:
    """Best-effort type inference from structural markers. Returns [] if none match."""
    inferred: list[str] = []
    memo_fields = {m.group(1).upper() for m in MEMO_HEADER_RE.finditer(text)}
    if len(memo_fields) >= 2:
        inferred.append("memo")
    if SUBJECT_LINE_RE.search(text):
        inferred.append("email")
    if SALUTATION_RE.match(text.strip()) and SIGNOFF_RE.search(text):
        inferred.append("letter")
    if MARKDOWN_HEADING_RE.search(text):
        inferred.append("blog")
    return inferred


def _collect(
    outcome: RuleViolation | SkippedRule | None,
    violations: list[RuleViolation],
    skipped: list[SkippedRule],
) -> None:
    if isinstance(outcome, RuleViolation):
        violations.append(outcome)
    elif isinstance(outcome, SkippedRule):
        skipped.append(outcome)


def run_checks(text: str, types: list[str] | None, repo: CorpusRepository) -> StandardsCheckResult:
    """Run all universal detectors plus addenda for the resolved type list."""
    resolved_types = list(types) if types else infer_types(text)

    violations: list[RuleViolation] = []
    skipped: list[SkippedRule] = []

    for detector in UNIVERSAL.values():
        _collect(detector(text, repo, resolved_types), violations, skipped)

    for type_name in resolved_types:
        entry = ADDENDA.get(type_name)
        if entry is None:
            continue
        _rule_id, detector = entry
        _collect(detector(text, repo, resolved_types), violations, skipped)

    return StandardsCheckResult(violations=violations, skipped_rules=skipped)
