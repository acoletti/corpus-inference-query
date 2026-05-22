"""Tests for writing-standards detectors."""
from __future__ import annotations

from corpus_inference_query.detectors import run_all
from corpus_inference_query.detectors.base import Violation
from corpus_inference_query.detectors.rules import (
    detect_clarity,
    detect_cohesion,
    detect_concision,
    detect_voice_agency,
)


class TestRegistry:
    def test_run_all_returns_dict_with_violations_and_skipped(self) -> None:
        result = run_all("Hello world.")
        assert "violations" in result
        assert "skipped_rules" in result
        assert isinstance(result["violations"], list)
        assert isinstance(result["skipped_rules"], list)

    def test_run_all_empty_text_no_error(self) -> None:
        result = run_all("")
        assert isinstance(result, dict)

    def test_voice_fidelity_always_in_skipped(self) -> None:
        result = run_all("Any text.")
        skipped_ids = {s["rule_id"] for s in result["skipped_rules"]}
        assert "§13" in skipped_ids

    def test_audience_fit_skipped_when_no_types(self) -> None:
        result = run_all("Some text.", types=None)
        skipped_ids = {s["rule_id"] for s in result["skipped_rules"]}
        assert "§7" in skipped_ids

    def test_type_addendum_not_applied_without_matching_type(self) -> None:
        result = run_all("Short text.", types=["essay"])
        violation_ids = {v["rule_id"] for v in result["violations"]}
        assert "§B" not in violation_ids  # email addendum should not fire

    def test_type_addendum_applied_with_matching_type(self) -> None:
        # With stubs returning [], violations should be empty but no error
        result = run_all("Short text.", types=["email"])
        assert isinstance(result["violations"], list)


class TestClarity:
    def test_long_sentence_flagged(self) -> None:
        long = "The committee which had been formed by the board which was appointed by the shareholders who voted at the meeting held in March decided to defer action pending further review of all available options."
        result = detect_clarity(long)
        assert result is not None
        assert len(result) == 1
        assert result[0].rule_id == "§1"
        assert result[0].severity == "warning"

    def test_short_clear_sentence_clean(self) -> None:
        assert detect_clarity("Sentences make readers.") == []

    def test_nested_relative_clauses_flagged(self) -> None:
        nested = "The report that the analyst who the firm hired last year wrote contained errors that mattered."
        result = detect_clarity(nested)
        assert result is not None and len(result) >= 1

    def test_multiple_sentences_one_long(self) -> None:
        text = "Dogs bark. " + "a " * 45 + "sentence."
        result = detect_clarity(text)
        assert len(result) == 1


class TestCohesion:
    def test_no_overlap_flagged(self) -> None:
        text = "Dogs are loyal. Quantum physics is complex."
        result = detect_cohesion(text)
        assert result is not None and len(result) >= 1

    def test_overlapping_sentences_clean(self) -> None:
        text = "The experiment failed. The failure was first noticed by the team."
        assert detect_cohesion(text) == []

    def test_single_sentence_not_flagged(self) -> None:
        assert detect_cohesion("Hello.") == []


class TestConcision:
    def test_wordy_phrase_flagged(self) -> None:
        text = "Due to the fact that the report was late, we met."
        result = detect_concision(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§3"

    def test_multiple_wordy_phrases(self) -> None:
        text = "In the event that we fail, due to the fact that resources are limited, we must act."
        result = detect_concision(text)
        assert len(result) >= 2

    def test_clean_sentence_no_violation(self) -> None:
        assert detect_concision("The report was late because resources were limited.") == []

    def test_very_unique_flagged(self) -> None:
        result = detect_concision("This is a very unique opportunity.")
        assert len(result) >= 1


class TestVoiceAgency:
    def test_high_passive_rate_flagged(self) -> None:
        passive = "The decision was made. The report was reviewed. The findings were approved. The plan was implemented."
        result = detect_voice_agency(passive)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§4"

    def test_active_sentences_clean(self) -> None:
        active = "The committee decided. They reviewed the report. The team approved the findings."
        assert detect_voice_agency(active) == []

    def test_high_nominalization_density_flagged(self) -> None:
        text = "The implementation of the transformation required the commitment of the organization to the achievement of the improvement."
        result = detect_voice_agency(text)
        assert result is not None and len(result) >= 1
