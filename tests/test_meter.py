"""Tests for the deterministic meter checker."""

from __future__ import annotations

import json

import pytest

from corpus_inference_query.meter import METERS, check_meter, line_syllables
from corpus_inference_query.tool_responses import (
    format_check_meter,
    format_check_meter_json,
)

# "Shall I compare thee to a summer's day" scans to 10 with the
# vowel-group approximation.
PENTAMETER_LINE = "Shall I compare thee to a summer's day"
SHORT_LINE = "The cat sat"  # 3 syllables


class TestLineSyllables:
    def test_pentameter_line(self) -> None:
        assert line_syllables(PENTAMETER_LINE) == 10

    def test_short_line(self) -> None:
        assert line_syllables(SHORT_LINE) == 3


class TestCheckMeter:
    def test_conforming_pentameter(self) -> None:
        result = check_meter(PENTAMETER_LINE, meter="iambic_pentameter")
        assert result.line_count == 1
        assert result.conforming_count == 1
        assert result.conformity_ratio == 1.0

    def test_off_meter_line_detected(self) -> None:
        result = check_meter(SHORT_LINE, meter="iambic_pentameter")
        assert result.conforming_count == 0
        assert result.lines[0].deviation == -7

    def test_tolerance_widens_conformity(self) -> None:
        text = "A nine or so syllable line right here"  # 9-ish
        strict = check_meter(text, meter="iambic_pentameter", tolerance=0)
        loose = check_meter(text, meter="iambic_pentameter", tolerance=2)
        assert loose.conforming_count >= strict.conforming_count

    def test_skips_scaffolding_lines(self) -> None:
        text = "\n".join([
            "# A Heading",
            "[AUTHOR: decide — something]",
            "",
            PENTAMETER_LINE,
        ])
        result = check_meter(text)
        assert result.line_count == 1

    def test_common_meter_alternates(self) -> None:
        result = check_meter("one\ntwo\nthree\nfour", meter="common_meter")
        assert [s.expected for s in result.lines] == [8, 6, 8, 6]

    def test_unknown_meter_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown meter"):
            check_meter("text", meter="sapphic")

    def test_empty_text(self) -> None:
        result = check_meter("")
        assert result.line_count == 0
        assert result.conformity_ratio == 0.0

    def test_all_named_meters_scan(self) -> None:
        for meter in METERS:
            result = check_meter(PENTAMETER_LINE, meter=meter)
            assert result.line_count == 1


class TestFormatCheckMeter:
    def test_markdown_all_conforming(self) -> None:
        out = format_check_meter(check_meter(PENTAMETER_LINE))
        assert "All lines conform" in out
        assert "stress placement is not verified" in out

    def test_markdown_off_meter_table(self) -> None:
        out = format_check_meter(check_meter(SHORT_LINE))
        assert "| Line |" in out
        assert "The cat sat" in out

    def test_markdown_empty(self) -> None:
        assert "No verse lines" in format_check_meter(check_meter(""))

    def test_json_shape(self) -> None:
        payload = json.loads(format_check_meter_json(check_meter(SHORT_LINE)))
        assert payload["status"] == "deviations"
        assert payload["meter"] == "iambic_pentameter"
        assert payload["off_meter_lines"][0]["deviation"] == -7

    def test_json_conforming_status(self) -> None:
        payload = json.loads(format_check_meter_json(check_meter(PENTAMETER_LINE)))
        assert payload["status"] == "conforming"
        assert payload["off_meter_lines"] == []
