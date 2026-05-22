"""Tests for tool_responses module."""

from __future__ import annotations

from corpus_inference_query.corpus_repository import CorpusSummary, ReloadResult
from corpus_inference_query.tool_responses import (
    format_check_stub,
    format_list_corpora,
    format_reload,
)


class TestFormatListCorpora:
    def test_table_with_corpora(self) -> None:
        summaries = [
            CorpusSummary(
                shorthand="HTWS",
                title="How to Write a Sentence",
                author="Stanley Fish",
                default_style=["subordinating"],
                default_type=["essay"],
                doc_count=5,
            ),
            CorpusSummary(
                shorthand="Strunk",
                title="The Elements of Style",
                author="Strunk & White",
                default_style=["minimalist"],
                default_type=["guide"],
                doc_count=3,
            ),
        ]
        result = format_list_corpora(summaries)
        assert "| Shorthand | Title | Author | Style Tags | Type Tags | Sections |" in result
        assert "| HTWS | How to Write a Sentence | Stanley Fish | subordinating | essay | 5 |" in result
        assert "| Strunk | The Elements of Style | Strunk & White | minimalist | guide | 3 |" in result
        assert "**Total**: 2 corpora, 8 sections indexed." in result

    def test_empty_list(self) -> None:
        assert format_list_corpora([]) == "No corpora configured."

    def test_multiple_tags(self) -> None:
        summaries = [
            CorpusSummary(
                shorthand="CC",
                title="Clean Code",
                author="Robert C. Martin",
                default_style=["formal", "technical"],
                default_type=["book", "reference"],
                doc_count=12,
            ),
        ]
        result = format_list_corpora(summaries)
        assert "formal, technical" in result
        assert "book, reference" in result

    def test_no_tags_renders_none(self) -> None:
        summaries = [
            CorpusSummary(
                shorthand="Test",
                title="Test Corpus",
                author="Test Author",
                default_style=[],
                default_type=[],
                doc_count=2,
            ),
        ]
        assert "none" in format_list_corpora(summaries)


class TestFormatReload:
    def test_single_corpus(self) -> None:
        result = ReloadResult(status="ok", corpora_count=1, doc_count=5)
        assert format_reload(result) == "Reloaded 5 sections from 1 corpora."

    def test_multiple_corpora(self) -> None:
        result = ReloadResult(status="ok", corpora_count=3, doc_count=42)
        assert format_reload(result) == "Reloaded 42 sections from 3 corpora."

    def test_zero_counts(self) -> None:
        result = ReloadResult(status="ok", corpora_count=0, doc_count=0)
        assert format_reload(result) == "Reloaded 0 sections from 0 corpora."


class TestFormatCheckStub:
    def test_with_types(self) -> None:
        result = {
            "status": "not_yet_implemented",
            "text_length": 150,
            "types_provided": ["essay", "guide"],
            "skipped_rules": ["all — detectors ship in M3"],
        }
        formatted = format_check_stub(result)
        assert "Standards check: not yet implemented (M3)." in formatted
        assert "Text length: 150 characters." in formatted
        assert "Configured types: essay, guide." in formatted

    def test_without_types(self) -> None:
        result = {
            "status": "not_yet_implemented",
            "text_length": 500,
            "types_provided": [],
            "skipped_rules": [],
        }
        formatted = format_check_stub(result)
        assert "Text length: 500 characters." in formatted
        assert "Configured types: none." in formatted

    def test_large_text(self) -> None:
        result = {
            "status": "not_yet_implemented",
            "text_length": 50000,
            "types_provided": ["novel"],
            "skipped_rules": ["all"],
        }
        assert "Text length: 50000 characters." in format_check_stub(result)
