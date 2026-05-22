"""Unit tests for tag_filter.py — pure predicate functions."""

from __future__ import annotations

from corpus_inference_query.indexer import Section
from corpus_inference_query.tag_filter import filter_sections, matches_tags


def _make_section(
    shorthand: str = "HTWS",
    style_tags: list[str] | None = None,
    type_tags: list[str] | None = None,
) -> Section:
    return Section(
        corpus_id="test",
        shorthand=shorthand,
        chapter="Ch",
        section_name="S",
        citation=f"{shorthand} §S",
        content="content",
        line_start=0,
        style_tags=style_tags or [],
        type_tags=type_tags or [],
    )


class TestMatchesTags:
    def test_no_filters_matches_everything(self) -> None:
        sec = _make_section(style_tags=["subordinating"], type_tags=["essay"])
        assert matches_tags(sec) is True

    def test_style_filter_exact_match(self) -> None:
        sec = _make_section(style_tags=["subordinating", "additive"])
        assert matches_tags(sec, style=["subordinating"]) is True

    def test_style_filter_requires_all_tags(self) -> None:
        sec = _make_section(style_tags=["subordinating"])
        assert matches_tags(sec, style=["subordinating", "additive"]) is False

    def test_type_filter_exact_match(self) -> None:
        sec = _make_section(type_tags=["essay", "book"])
        assert matches_tags(sec, type_filter=["essay"]) is True

    def test_type_filter_requires_all_tags(self) -> None:
        sec = _make_section(type_tags=["essay"])
        assert matches_tags(sec, type_filter=["essay", "book"]) is False

    def test_corpus_filter_match(self) -> None:
        sec = _make_section(shorthand="HTWS")
        assert matches_tags(sec, corpus="HTWS") is True

    def test_corpus_filter_no_match(self) -> None:
        sec = _make_section(shorthand="Strunk")
        assert matches_tags(sec, corpus="HTWS") is False

    def test_all_filters_must_pass(self) -> None:
        sec = _make_section(
            shorthand="HTWS",
            style_tags=["subordinating"],
            type_tags=["essay"],
        )
        assert matches_tags(sec, style=["subordinating"], type_filter=["essay"], corpus="HTWS") is True
        assert matches_tags(sec, style=["additive"], type_filter=["essay"], corpus="HTWS") is False

    def test_empty_section_tags_no_match_on_filter(self) -> None:
        sec = _make_section(style_tags=[], type_tags=[])
        assert matches_tags(sec, style=["subordinating"]) is False


class TestFilterSections:
    def test_no_filters_returns_all(self) -> None:
        secs = [_make_section("HTWS"), _make_section("Strunk")]
        assert filter_sections(secs) == secs

    def test_corpus_filter_narrows(self) -> None:
        secs = [_make_section("HTWS"), _make_section("Strunk")]
        result = filter_sections(secs, corpus="HTWS")
        assert len(result) == 1
        assert result[0].shorthand == "HTWS"

    def test_style_filter_narrows(self) -> None:
        secs = [
            _make_section(style_tags=["subordinating"]),
            _make_section(style_tags=["additive"]),
        ]
        result = filter_sections(secs, style=["subordinating"])
        assert len(result) == 1
        assert result[0].style_tags == ["subordinating"]

    def test_returns_empty_when_no_match(self) -> None:
        secs = [_make_section(style_tags=["additive"])]
        assert filter_sections(secs, style=["subordinating"]) == []
