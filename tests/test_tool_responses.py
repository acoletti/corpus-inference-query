"""Tests for tool_responses module."""

from __future__ import annotations

from corpus_inference_query.corpus_repository import CorpusSummary, ReloadResult
from corpus_inference_query.detectors.types import (
    RuleViolation,
    SkippedRule,
    StandardsCheckResult,
)
from corpus_inference_query.tool_responses import (
    format_check_against_standards,
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


class TestFormatCheckAgainstStandards:
    def test_no_violations_no_skips(self) -> None:
        result = StandardsCheckResult(violations=[], skipped_rules=[])
        assert format_check_against_standards(result) == "No standards violations detected."

    def test_violations_render_as_table(self) -> None:
        result = StandardsCheckResult(
            violations=[
                RuleViolation(
                    rule_id="§3",
                    rule_title="Concision",
                    severity="warning",
                    span=(0, 10),
                    snippet="each and every",
                    exemplar_citation="Strunk §Omit Needless Words",
                    suggested_rewrite_from_exemplar="Vigorous writing is concise.",
                ),
            ],
            skipped_rules=[],
        )
        formatted = format_check_against_standards(result)
        assert "| Rule | Title | Severity | Snippet | Exemplar |" in formatted
        assert "| §3 | Concision | warning | each and every | Strunk §Omit Needless Words |" in formatted

    def test_skipped_rules_render(self) -> None:
        result = StandardsCheckResult(
            violations=[],
            skipped_rules=[SkippedRule(rule_id="§13", reason_code="personal_corpus_empty")],
        )
        formatted = format_check_against_standards(result)
        assert "**Skipped rules**: §13 (personal_corpus_empty)." in formatted

    def test_violations_and_skips_both_render(self) -> None:
        result = StandardsCheckResult(
            violations=[
                RuleViolation(
                    rule_id="§1",
                    rule_title="Clarity",
                    severity="warning",
                    span=None,
                    snippet="a very long sentence",
                    exemplar_citation=None,
                    suggested_rewrite_from_exemplar=None,
                ),
            ],
            skipped_rules=[SkippedRule(rule_id="§7", reason_code="type_unknown")],
        )
        formatted = format_check_against_standards(result)
        assert "§1" in formatted
        assert "**Skipped rules**: §7 (type_unknown)." in formatted
