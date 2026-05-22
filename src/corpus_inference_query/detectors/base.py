"""Violation and SkipResult dataclasses for standards detectors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Violation:
    rule_id: str
    rule_title: str
    severity: str  # "error" | "warning" | "info"
    snippet: str
    span: tuple[int, int] | None = None
    exemplar_citation: str | None = None
    suggested_rewrite_from_exemplar: str | None = None


@dataclass
class SkipResult:
    rule_id: str
    rule_title: str
    reason: str  # "personal_corpus_empty" | "type_unknown" | "vector_backend_unavailable"


DetectorFn = Callable[[str, "list[str] | None"], "list[Violation] | None"]
