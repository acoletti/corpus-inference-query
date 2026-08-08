"""Result types shared by all standards-rule detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["warning", "info"]
SkipReason = Literal[
    "personal_corpus_empty",
    "type_unknown",
    "vector_backend_unavailable",
]


@dataclass
class RuleViolation:
    rule_id: str
    rule_title: str
    severity: Severity
    span: tuple[int, int] | None
    snippet: str
    exemplar_citation: str | None
    suggested_rewrite_from_exemplar: str | None


@dataclass
class SkippedRule:
    rule_id: str
    reason_code: SkipReason


@dataclass
class StandardsCheckResult:
    violations: list[RuleViolation]
    skipped_rules: list[SkippedRule]
