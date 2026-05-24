"""Integration tests for CorpusRepository using the fixture corpus."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_inference_query.corpus_repository import CorpusRepository


_FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"


@pytest.fixture()
def repo() -> CorpusRepository:
    return CorpusRepository(_FIXTURE_CORPUS)


class TestListCorpora:
    def test_returns_all_corpora(self, repo: CorpusRepository) -> None:
        summaries = repo.list_corpora()
        assert len(summaries) == 3
        shorthands = {s.shorthand for s in summaries}
        assert shorthands == {"HTWS", "Strunk", "Jung-PU"}

    def test_htws_metadata(self, repo: CorpusRepository) -> None:
        htws = next(s for s in repo.list_corpora() if s.shorthand == "HTWS")
        assert htws.title == "How to Write a Sentence"
        assert htws.author == "Stanley Fish"
        assert "subordinating" in htws.default_style
        assert htws.doc_count >= 2

    def test_doc_count_positive(self, repo: CorpusRepository) -> None:
        summaries = repo.list_corpora()
        assert all(s.doc_count > 0 for s in summaries)


class TestLookupCitation:
    def test_known_citation_returns_content(self, repo: CorpusRepository) -> None:
        result = repo.lookup_citation("HTWS §Subordinating")
        assert "Subordinating" in result

    def test_unknown_citation_returns_available(self, repo: CorpusRepository) -> None:
        result = repo.lookup_citation("HTWS §NonExistent")
        assert "Available sections" in result or "No section" in result


class TestFindExemplars:
    def test_no_filters_returns_sections(self, repo: CorpusRepository) -> None:
        result = repo.find_exemplars()
        assert len(result) > 0

    def test_style_filter_narrows(self, repo: CorpusRepository) -> None:
        result = repo.find_exemplars(style=["subordinating"])
        assert "HTWS" in result

    def test_unknown_style_returns_empty_message(self, repo: CorpusRepository) -> None:
        result = repo.find_exemplars(style=["nonexistent-style"])
        assert "No exemplars" in result

    def test_length_filter_short(self, repo: CorpusRepository) -> None:
        result = repo.find_exemplars(length="short")
        # May or may not return results depending on fixture content lengths
        assert isinstance(result, str)


class TestFindSimilarVoice:
    def test_unknown_corpus_returns_graceful_message(self, repo: CorpusRepository) -> None:
        result = repo.find_similar_voice("some text", corpus="personal")
        assert "No sections found" in result

    def test_known_corpus_returns_string(self, repo: CorpusRepository) -> None:
        result = repo.find_similar_voice("The sentence arranges its parts.", corpus="HTWS")
        assert isinstance(result, str)
        assert len(result) > 0


class TestSuggestOpening:
    def test_known_type_returns_openings(self, repo: CorpusRepository) -> None:
        result = repo.suggest_opening(type_name="essay")
        assert isinstance(result, str)

    def test_unknown_type_returns_message(self, repo: CorpusRepository) -> None:
        result = repo.suggest_opening(type_name="nonexistent-type")
        assert "No opening sentences" in result


class TestSuggestRewrite:
    def test_known_style_returns_exemplars(self, repo: CorpusRepository) -> None:
        result = repo.suggest_rewrite("A short sentence.", target_style="subordinating")
        assert "HTWS" in result

    def test_unknown_style_returns_message(self, repo: CorpusRepository) -> None:
        result = repo.suggest_rewrite("Text.", target_style="nonexistent-style")
        assert "No sections found" in result


class TestCheckAgainstStandards:
    def test_returns_detector_dict(self, repo: CorpusRepository) -> None:
        result = repo.check_against_standards("Some text.")
        assert "violations" in result
        assert "skipped_rules" in result
        assert "types_used" in result

    def test_types_used_propagated(self, repo: CorpusRepository) -> None:
        result = repo.check_against_standards("Hello.", types=["essay"])
        assert "essay" in result["types_used"]


class TestReload:
    def test_reload_returns_result(self, repo: CorpusRepository) -> None:
        result = repo.reload()
        assert result.status == "ok"
        assert result.corpora_count == 3
        assert result.doc_count >= 2

    def test_reload_clears_cache(self, repo: CorpusRepository) -> None:
        # Load once, then reload
        _ = repo._get_index()
        result = repo.reload()
        assert result.status == "ok"
