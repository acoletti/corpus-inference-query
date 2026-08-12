"""Tests for the deterministic cadence/flow checker."""

from __future__ import annotations

import json

import pytest

from corpus_inference_query.flow import check_flow
from corpus_inference_query.tool_responses import (
    format_check_flow,
    format_check_flow_json,
)

# 11 of 12 lines open with "and" — the drafter-20260810-223054 failure shape.
MONOTONE_VERSE = "\n".join(
    ["I shut one door and left the room quite bare,"]
    + [f"and still a tenant scratches at the wood {i}," for i in range(11)]
)

VARIED_VERSE = """The door swung shut behind me in the hall,
a tenant scratched the wood, insistent, low.
Twilight came down. I poured two cups of tea
and set them on the sill, and no one spoke.
Light returned by morning, unannounced.
Less is buried now. The rest can wait."""

UNIFORM_PROSE = " ".join(
    f"The cat sat on the warm mat today number {i}." for i in range(8)
)

VARIED_PROSE = (
    "It rained. The storm that had been building over the western ridge all "
    "afternoon finally broke across the valley with a violence nobody had "
    "predicted. We ran. Later, soaked and laughing in the barn doorway, she "
    "asked me why I had waited so long to say anything at all. I had no answer."
)


class TestUnitResolution:
    def test_auto_detects_verse(self) -> None:
        assert check_flow(MONOTONE_VERSE).unit == "lines"

    def test_auto_detects_prose(self) -> None:
        assert check_flow(VARIED_PROSE).unit == "sentences"

    def test_forced_units(self) -> None:
        assert check_flow(VARIED_PROSE, unit="lines").unit == "lines"
        assert check_flow(MONOTONE_VERSE, unit="sentences").unit == "sentences"

    def test_unknown_unit_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown unit"):
            check_flow("x", unit="stanzas")

    def test_scaffolding_skipped(self) -> None:
        text = "# Title\n\n[AUTHOR: add a scene]\nOne real line here\nAnother line follows now"
        assert check_flow(text, unit="lines").unit_count == 2

    def test_empty_text(self) -> None:
        result = check_flow("")
        assert result.status == "empty"
        assert result.unit_count == 0


class TestMonotonyDetection:
    def test_opener_run_and_dominance_flagged(self) -> None:
        result = check_flow(MONOTONE_VERSE)
        categories = {f.category for f in result.findings}
        assert "opener_run" in categories
        assert "opener_dominance" in categories
        assert result.status == "monotone"
        assert result.top_opener == "and"
        assert result.longest_opener_run >= 4

    def test_repeated_trigram_flagged(self) -> None:
        result = check_flow(MONOTONE_VERSE)
        grams = [f.evidence for f in result.findings if f.category == "repeated_ngram"]
        assert grams
        assert any("tenant" in g for g in grams)

    def test_uniform_sentence_length_flagged(self) -> None:
        result = check_flow(UNIFORM_PROSE)
        assert "uniform_length" in {f.category for f in result.findings}

    def test_uniform_length_not_checked_in_verse(self) -> None:
        result = check_flow(MONOTONE_VERSE)
        assert "uniform_length" not in {f.category for f in result.findings}


class TestVariedTextPasses:
    def test_varied_verse_clean(self) -> None:
        result = check_flow(VARIED_VERSE)
        assert result.status == "varied"
        assert result.findings == []

    def test_varied_prose_clean(self) -> None:
        result = check_flow(VARIED_PROSE)
        assert result.status == "varied"
        assert result.findings == []

    def test_short_text_skips_ratio_checks(self) -> None:
        result = check_flow("And one. And two. And three.")
        assert "opener_dominance" not in {f.category for f in result.findings}


class TestFormatters:
    def test_markdown_monotone_has_table(self) -> None:
        out = format_check_flow(check_flow(MONOTONE_VERSE))
        assert "| Category |" in out
        assert "opener_run" in out

    def test_markdown_varied_no_table(self) -> None:
        out = format_check_flow(check_flow(VARIED_VERSE))
        assert "No monotony markers detected" in out

    def test_markdown_empty(self) -> None:
        assert format_check_flow(check_flow("")) == "No units found to scan."

    def test_json_payload_shape(self) -> None:
        payload = json.loads(format_check_flow_json(check_flow(MONOTONE_VERSE)))
        assert payload["status"] == "monotone"
        assert payload["unit"] == "lines"
        assert payload["findings"]
        assert {"category", "detail", "evidence"} <= set(payload["findings"][0])

    def test_json_varied_status(self) -> None:
        payload = json.loads(format_check_flow_json(check_flow(VARIED_PROSE)))
        assert payload["status"] == "varied"
        assert payload["findings"] == []
