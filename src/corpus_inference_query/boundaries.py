"""Writing-boundary models: Pydantic v2 contracts for LLM-produced editorial
review and debate outputs.

These are LLM-output boundaries in the sense of the translator Phase 2 spec —
frozen Pydantic models validated at the orchestrator/agent seam. Config and
detector types elsewhere in this package remain stdlib frozen dataclasses;
Pydantic is used only where free-form LLM text is parsed into structure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCORECARD_DIMENSIONS = ("craft", "voice", "structure", "truth", "risk")

PriorityLevel = Literal["HIGH", "MEDIUM", "LOW"]


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


BOUNDARY_MODELS: dict[str, type[BaseModel]] = {
    "review": EditorialReview,
    "debate": DebateResponse,
    "scorecard": Scorecard,
}
