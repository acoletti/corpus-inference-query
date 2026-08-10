"""Tests for writing-boundary models and the validate_boundary formatter."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from corpus_inference_query.boundaries import (
    BOUNDARY_MODELS,
    DebateResponse,
    EditorialReview,
    Scorecard,
)
from corpus_inference_query.tool_responses import format_validate_boundary


def _observation(n: int) -> dict:
    return {"quote": f"quoted passage {n}", "comment": f"comment {n}"}


def _valid_review() -> dict:
    return {
        "persona": "Fish",
        "first_impression": "Tight, propulsive prose.",
        "what_works": [_observation(i) for i in range(3)],
        "what_needs_work": [_observation(i) for i in range(3)],
        "central_question": "What is the sentence's real subject?",
        "priorities": [{"level": "HIGH", "summary": "Fix the opening."}],
        "scorecard": {"craft": 4, "voice": 3, "structure": 3, "truth": 4, "risk": 3},
    }


class TestScorecard:
    def test_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            Scorecard(craft=6, voice=3, structure=3, truth=3, risk=3)

    def test_over_smoothing_signature(self) -> None:
        smooth = Scorecard(craft=5, voice=2, structure=4, truth=4, risk=3)
        healthy = Scorecard(craft=4, voice=4, structure=4, truth=4, risk=4)
        assert smooth.over_smoothing_signature()
        assert not healthy.over_smoothing_signature()


class TestEditorialReview:
    def test_valid_review_parses(self) -> None:
        review = EditorialReview.model_validate(_valid_review())
        assert review.persona == "Fish"

    def test_central_question_must_be_question(self) -> None:
        data = _valid_review()
        data["central_question"] = "Fix the opening paragraph."
        with pytest.raises(ValidationError):
            EditorialReview.model_validate(data)

    def test_single_word_quote_rejected(self) -> None:
        data = _valid_review()
        data["what_works"][0]["quote"] = "word"
        with pytest.raises(ValidationError):
            EditorialReview.model_validate(data)

    def test_observation_counts_enforced(self) -> None:
        data = _valid_review()
        data["what_works"] = [_observation(0)]
        with pytest.raises(ValidationError):
            EditorialReview.model_validate(data)

    def test_frozen(self) -> None:
        review = EditorialReview.model_validate(_valid_review())
        with pytest.raises(ValidationError):
            review.persona = "Woolf"


class TestDebateResponse:
    def test_valid_debate_parses(self) -> None:
        debate = DebateResponse.model_validate({
            "persona": "Nabokov",
            "disagreements": [{
                "reviewer": "Fish",
                "claim": "The repetition should be cut.",
                "response": "The repetition is the voice.",
            }],
            "what_others_missed": "The sonic pattern in paragraph two.",
            "revised_priorities": [{"level": "HIGH", "summary": "Keep the repetition."}],
            "defended_dissent": True,
        })
        assert debate.defended_dissent

    def test_revised_priorities_capped_at_three(self) -> None:
        with pytest.raises(ValidationError):
            DebateResponse.model_validate({
                "persona": "Fish",
                "what_others_missed": "x",
                "revised_priorities": [
                    {"level": "LOW", "summary": f"p{i}"} for i in range(4)
                ],
            })


class TestFormatValidateBoundary:
    def test_valid_payload(self) -> None:
        out = json.loads(format_validate_boundary(
            json.dumps(_valid_review()), "review", BOUNDARY_MODELS,
        ))
        assert out["status"] == "valid"
        assert out["artifact"]["persona"] == "Fish"
        assert out["flags"]["over_smoothing_signature"] is False

    def test_scorecard_flag_surfaces(self) -> None:
        payload = {"craft": 5, "voice": 1, "structure": 4, "truth": 4, "risk": 2}
        out = json.loads(format_validate_boundary(
            json.dumps(payload), "scorecard", BOUNDARY_MODELS,
        ))
        assert out["flags"]["over_smoothing_signature"] is True

    def test_invalid_payload_reports_locations(self) -> None:
        data = _valid_review()
        del data["central_question"]
        out = json.loads(format_validate_boundary(
            json.dumps(data), "review", BOUNDARY_MODELS,
        ))
        assert out["status"] == "invalid"
        assert ["central_question"] in [e["loc"] for e in out["errors"]]

    def test_unknown_boundary(self) -> None:
        out = json.loads(format_validate_boundary("{}", "sonnet", BOUNDARY_MODELS))
        assert out["status"] == "invalid"
        assert "unknown boundary" in out["errors"][0]["msg"]

    def test_malformed_json(self) -> None:
        out = json.loads(format_validate_boundary("{not json", "review", BOUNDARY_MODELS))
        assert out["status"] == "invalid"
        assert out["errors"][0]["type"] == "json_error"
