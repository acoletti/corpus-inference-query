"""Tests for writing-boundary models and the validate_boundary formatter."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from corpus_inference_query.boundaries import (
    BOUNDARY_MODELS,
    AISmellBoundary,
    DebateResponse,
    EditorialReview,
    ParataxisScorecard,
    Scorecard,
    smell_flags,
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

    def test_high_ai_likelihood_flag_surfaces(self) -> None:
        out = json.loads(format_validate_boundary(
            json.dumps(_valid_ai_smell(risk="high")), "ai_smell", BOUNDARY_MODELS,
        ))
        assert out["status"] == "valid"
        assert out["flags"]["high_ai_likelihood"] is True

    def test_flatline_flag_surfaces(self) -> None:
        payload = {
            "persona": "Parataxis Specialist",
            "ligature_integrity": 3,
            "string_rhythm": 2,
            "unit_weight": 1,
            "landing": 3,
            "fake_parataxis_count": 2,
        }
        out = json.loads(format_validate_boundary(
            json.dumps(payload), "parataxis_scorecard", BOUNDARY_MODELS,
        ))
        assert out["flags"]["flatline_signature"] is True


def _valid_ai_smell(risk: str = "medium") -> dict:
    findings = [] if risk == "clean" else [{
        "quote": "this isn't a meal, it's a journey",
        "marker": "negate_then_assert",
        "repair": "The meal runs nine courses and takes three hours.",
    }]
    return {
        "persona": "AI Smell Detector",
        "risk_level": risk,
        "findings": findings,
        "burstiness_note": "Sentence lengths cluster at 18-22 words throughout.",
        "verdict": "Two banned pivots and uniform rhythm.",
    }


class TestSmellFlags:
    def test_negate_then_assert_detected(self) -> None:
        assert "negate_then_assert" in smell_flags("It isn't a meal, it's a journey.")

    def test_hype_words_detected(self) -> None:
        assert "hype_filler" in smell_flags("A rich tapestry of flavors.")

    def test_canned_transition_detected(self) -> None:
        assert "canned_transition" in smell_flags("Furthermore, the dish sings.")

    def test_clean_text_passes(self) -> None:
        assert smell_flags("The soup was cold. Nobody sent it back.") == []


class TestAISmellBoundary:
    def test_valid_payload_parses(self) -> None:
        smell = AISmellBoundary.model_validate(_valid_ai_smell())
        assert smell.risk_level == "medium"
        assert not smell.high_ai_likelihood()

    def test_high_risk_gates(self) -> None:
        assert AISmellBoundary.model_validate(
            _valid_ai_smell(risk="high")).high_ai_likelihood()

    def test_non_clean_requires_findings(self) -> None:
        data = _valid_ai_smell(risk="high")
        data["findings"] = []
        with pytest.raises(ValidationError):
            AISmellBoundary.model_validate(data)

    def test_clean_forbids_findings(self) -> None:
        data = _valid_ai_smell(risk="clean")
        data["findings"] = _valid_ai_smell()["findings"]
        with pytest.raises(ValidationError):
            AISmellBoundary.model_validate(data)

    def test_smelly_repair_rejected(self) -> None:
        data = _valid_ai_smell()
        data["findings"][0]["repair"] = "It isn't fuel — it's a curated journey."
        with pytest.raises(ValidationError):
            AISmellBoundary.model_validate(data)

    def test_unknown_marker_rejected(self) -> None:
        data = _valid_ai_smell()
        data["findings"][0]["marker"] = "sounds_robotic"
        with pytest.raises(ValidationError):
            AISmellBoundary.model_validate(data)


class TestParataxisScorecard:
    def test_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            ParataxisScorecard(
                persona="Parataxis Specialist", ligature_integrity=6,
                string_rhythm=3, unit_weight=3, landing=3, fake_parataxis_count=0)

    def test_flatline_signature(self) -> None:
        flat = ParataxisScorecard(
            persona="Parataxis Specialist", ligature_integrity=3,
            string_rhythm=2, unit_weight=2, landing=3, fake_parataxis_count=1)
        pulsing = ParataxisScorecard(
            persona="Parataxis Specialist", ligature_integrity=4,
            string_rhythm=4, unit_weight=4, landing=5, fake_parataxis_count=0)
        assert flat.flatline_signature()
        assert not pulsing.flatline_signature()
