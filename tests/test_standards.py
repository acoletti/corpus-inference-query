"""Tests for writing-standards detectors."""
from __future__ import annotations

from corpus_inference_query.detectors import run_all
from corpus_inference_query.detectors.base import Violation


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
