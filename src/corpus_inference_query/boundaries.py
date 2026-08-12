"""Writing-boundary models: Pydantic v2 contracts for LLM-produced editorial
review and debate outputs.

These are LLM-output boundaries in the sense of the translator Phase 2 spec —
frozen Pydantic models validated at the orchestrator/agent seam. Config and
detector types elsewhere in this package remain stdlib frozen dataclasses;
Pydantic is used only where free-form LLM text is parsed into structure.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCORECARD_DIMENSIONS = ("craft", "voice", "structure", "truth", "risk")

PriorityLevel = Literal["HIGH", "MEDIUM", "LOW"]

RiskLevel = Literal["clean", "low", "medium", "high"]

# Deterministic AI-smell checks, ported from sendme lib/llm/writing-style.ts
# (smellsLikeAI) via translator ingest/smell.py. Used to reject proposed
# repairs that themselves carry banned LLM constructions.
_NEGATE_ASSERT = re.compile(
    r"\b(isn'?t|aren'?t|wasn'?t|weren'?t|don'?t|doesn'?t|didn'?t|won'?t)\b"
    r"[^.!?;]{0,60}\b(it'?s|they'?re|you'?re)\b")
_NOT_JUST = re.compile(r"\bnot (just|merely|simply|only a)\b")
_MORE_THAN_JUST = re.compile(r"\bmore than (just|merely)\b")
_DONT_JUST = re.compile(r"\bdon'?t just\b")
_PIVOT = re.compile(r"[;\u2014]\s*(it'?s|you'?re|they'?re)\b")
_KIND_FOR = re.compile(
    r"\bthe kind (of|you)\b[^.!?]{0,40}\b(that|wired|built|made) for\b")
_HYPE_WORDS = re.compile(
    r"\b(delve|tapestry|testament|beacon|realm of|landscape of|"
    r"elevat(?:e|ed|ing)|unlock(?:ed|ing)?|immersive|seamless(?:ly)?|curated|"
    r"at its core|in a world where|journey of|"
    r"truly|deeply|utterly|genuinely)\b")
_TRANSITION_OPENER = re.compile(
    r"(?:^|[.!?]\s+)(furthermore|moreover|additionally|in conclusion)\b,?",
    re.MULTILINE)

AI_SMELL_CHECKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("negate_then_assert", _NEGATE_ASSERT),
    ("not_just", _NOT_JUST),
    ("more_than_just", _MORE_THAN_JUST),
    ("dont_just", _DONT_JUST),
    ("dramatic_pivot", _PIVOT),
    ("kind_built_for", _KIND_FOR),
    ("hype_filler", _HYPE_WORDS),
    ("canned_transition", _TRANSITION_OPENER),
)

AI_SMELL_MARKERS = tuple(name for name, _ in AI_SMELL_CHECKS) + (
    "uniform_burstiness",
    "templated_structure",
    "reader_characterization",
)


def smell_flags(text: str) -> list[str]:
    """Names of every banned construction found in the text (empty = clean)."""
    if not text:
        return []
    lowered = text.lower()
    return [name for name, pattern in AI_SMELL_CHECKS if pattern.search(lowered)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Scorecard(_Frozen):
    """1-5 scores on the five board dimensions (5 = fully achieved)."""

    craft: int = Field(ge=1, le=5)
    voice: int = Field(ge=1, le=5)
    structure: int = Field(ge=1, le=5)
    truth: int = Field(ge=1, le=5)
    risk: int = Field(ge=1, le=5)

    def over_smoothing_signature(self) -> bool:
        """Craft high while voice/risk low — the homogenization fingerprint."""
        return self.craft >= 4 and (self.voice <= 2 or self.risk <= 2)


class Observation(_Frozen):
    """One works/needs-work observation; must quote the text under review."""

    quote: str = Field(min_length=1)
    comment: str = Field(min_length=1)

    @field_validator("quote")
    @classmethod
    def _quote_is_substantive(cls, v: str) -> str:
        if len(v.split()) < 2:
            raise ValueError("quote must excerpt at least two words of the text")
        return v


class PriorityItem(_Frozen):
    level: PriorityLevel
    summary: str = Field(min_length=1)


class EditorialReview(_Frozen):
    """Phase 2 independent review — mirrors templates/review.md sections."""

    persona: str = Field(min_length=1)
    first_impression: str = Field(min_length=1)
    what_works: list[Observation] = Field(min_length=3, max_length=5)
    what_needs_work: list[Observation] = Field(min_length=3, max_length=5)
    central_question: str = Field(min_length=1)
    priorities: list[PriorityItem] = Field(min_length=1)
    scorecard: Scorecard

    @field_validator("central_question")
    @classmethod
    def _is_a_question(cls, v: str) -> str:
        if "?" not in v:
            raise ValueError("central_question must be framed as a question")
        return v


class DebatePoint(_Frozen):
    """One agreement/disagreement, attributed to a named reviewer."""

    reviewer: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    response: str = Field(min_length=1)


class DebateResponse(_Frozen):
    """Phase 3 debate — mirrors templates/debate.md sections."""

    persona: str = Field(min_length=1)
    agreements: list[DebatePoint] = Field(default_factory=list)
    disagreements: list[DebatePoint] = Field(default_factory=list)
    what_others_missed: str = Field(min_length=1)
    revised_priorities: list[PriorityItem] = Field(min_length=1, max_length=3)
    defended_dissent: bool = False


class AISmellFinding(_Frozen):
    """One detected AI-signature construction with its additive repair."""

    quote: str = Field(min_length=1)
    marker: str = Field(min_length=1)
    repair: str = Field(min_length=1)

    @field_validator("marker")
    @classmethod
    def _marker_is_known(cls, v: str) -> str:
        if v not in AI_SMELL_MARKERS:
            raise ValueError(f"unknown marker '{v}'; expected one of {sorted(AI_SMELL_MARKERS)}")
        return v

    @field_validator("repair")
    @classmethod
    def _repair_is_clean(cls, v: str) -> str:
        hits = smell_flags(v)
        if hits:
            raise ValueError(
                f"repair itself carries banned constructions: {hits}; "
                "state what is, never what is not")
        return v


class AISmellBoundary(_Frozen):
    """AI Smell Detector review — risk verdict plus per-construction findings.

    A `high` risk_level is the hard-gate signal: the orchestrator flags the
    reviewed suggestion as High AI Likelihood and excludes it from the
    primary recommendation roadmap.
    """

    persona: str = Field(min_length=1)
    risk_level: RiskLevel
    findings: list[AISmellFinding] = Field(default_factory=list)
    burstiness_note: str = Field(min_length=1)
    verdict: str = Field(min_length=1)

    @model_validator(mode="after")
    def _findings_support_risk(self) -> "AISmellBoundary":
        if self.risk_level != "clean" and not self.findings:
            raise ValueError("non-clean risk_level requires at least one finding")
        if self.risk_level == "clean" and self.findings:
            raise ValueError("clean risk_level must carry no findings")
        return self

    def high_ai_likelihood(self) -> bool:
        return self.risk_level == "high"


class ParataxisScorecard(_Frozen):
    """1-5 scores on coordinate-string craft (5 = fully achieved)."""

    persona: str = Field(min_length=1)
    ligature_integrity: int = Field(ge=1, le=5)
    string_rhythm: int = Field(ge=1, le=5)
    unit_weight: int = Field(ge=1, le=5)
    landing: int = Field(ge=1, le=5)
    fake_parataxis_count: int = Field(ge=0)

    def flatline_signature(self) -> bool:
        """Rhythm and unit-weight both low — the monotone-string fingerprint."""
        return self.string_rhythm <= 2 and self.unit_weight <= 2


FlowLevel = Literal["varied", "acceptable", "monotone"]

CADENCE_ISSUES = (
    "opener_run",
    "opener_dominance",
    "repeated_ngram",
    "uniform_length",
    "connective_monotony",
    "missing_turn",
    "flat_arc",
)


class CadenceFinding(_Frozen):
    """One flow/monotony finding with its additive repair directive."""

    quote: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    directive: str = Field(min_length=1)

    @field_validator("issue")
    @classmethod
    def _issue_is_known(cls, v: str) -> str:
        if v not in CADENCE_ISSUES:
            raise ValueError(f"unknown issue '{v}'; expected one of {sorted(CADENCE_ISSUES)}")
        return v

    @field_validator("directive")
    @classmethod
    def _directive_is_clean(cls, v: str) -> str:
        hits = smell_flags(v)
        if hits:
            raise ValueError(
                f"directive itself carries banned constructions: {hits}; "
                "state what is, never what is not")
        return v


class CadenceVerdict(_Frozen):
    """Cadence Reviewer verdict — flow level plus per-passage directives.

    A `monotone` flow_level joins the Drafter repair loop: each finding's
    directive is applied in the single shared repair pass.
    """

    persona: str = Field(min_length=1)
    flow_level: FlowLevel
    findings: list[CadenceFinding] = Field(default_factory=list)
    arc_note: str = Field(min_length=1)
    verdict: str = Field(min_length=1)

    @model_validator(mode="after")
    def _findings_support_level(self) -> "CadenceVerdict":
        if self.flow_level == "monotone" and not self.findings:
            raise ValueError("monotone flow_level requires at least one finding")
        return self


DraftDisposition = Literal["applied", "placeholder", "deferred"]


class DraftManifestItem(_Frozen):
    """One roadmap entry's disposition in the drafted revision."""

    roadmap_item: str = Field(min_length=1)
    disposition: DraftDisposition
    note: str = Field(min_length=1)

    @model_validator(mode="after")
    def _deferred_needs_reason(self) -> "DraftManifestItem":
        if self.disposition == "deferred" and len(self.note.split()) < 3:
            raise ValueError("a deferred item must state its reason in the note")
        return self


class DraftManifest(_Frozen):
    """Phase 5 Drafter change manifest — mirrors templates/draft.md section I.

    The Drafter applies only mechanical/structural edits; author-only work
    becomes [AUTHOR: ...] placeholders counted in `placeholder_count`.
    """

    persona: str = Field(min_length=1)
    items: list[DraftManifestItem] = Field(min_length=1)
    placeholder_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _placeholders_are_accounted(self) -> "DraftManifest":
        marked = sum(1 for i in self.items if i.disposition == "placeholder")
        if marked > 0 and self.placeholder_count == 0:
            raise ValueError(
                "items marked placeholder but placeholder_count is 0")
        return self


BOUNDARY_MODELS: dict[str, type[BaseModel]] = {
    "review": EditorialReview,
    "debate": DebateResponse,
    "scorecard": Scorecard,
    "ai_smell": AISmellBoundary,
    "parataxis_scorecard": ParataxisScorecard,
    "draft": DraftManifest,
    "cadence": CadenceVerdict,
}
