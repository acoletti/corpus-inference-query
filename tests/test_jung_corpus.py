"""Tests for Jung corpus indexing and concept tool integration."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"

os.environ.setdefault("CORPUS_INFERENCE_PATH", str(FIXTURE_CORPUS))


def _reset_repo():
    import corpus_inference_query.server as srv
    srv._repo = None


@pytest.fixture(autouse=True)
def _fresh_repo():
    _reset_repo()
    yield
    _reset_repo()


class TestJungCorpusIndexing:
    def test_jung_sections_indexed(self) -> None:
        from corpus_inference_query.indexer import build_index
        sections = build_index(FIXTURE_CORPUS)
        jung = [s for s in sections if s.corpus_id == "jung-psychology-unconscious"]
        assert len(jung) > 0, "No Jung sections indexed"

    def test_jung_sections_have_style_tags(self) -> None:
        from corpus_inference_query.indexer import build_index
        sections = build_index(FIXTURE_CORPUS)
        jung = [s for s in sections if s.corpus_id == "jung-psychology-unconscious"]
        for s in jung:
            assert "analytical" in s.style_tags

    def test_jung_sections_have_type_tags(self) -> None:
        from corpus_inference_query.indexer import build_index
        sections = build_index(FIXTURE_CORPUS)
        jung = [s for s in sections if s.corpus_id == "jung-psychology-unconscious"]
        for s in jung:
            assert "psychology" in s.type_tags

    def test_jung_uses_paragraph_group_chunking(self) -> None:
        from corpus_inference_query.indexer import build_index
        sections = build_index(FIXTURE_CORPUS)
        jung = [s for s in sections if s.corpus_id == "jung-psychology-unconscious"]
        has_paragraph_range = any("p0-" in s.section_name or "(p" in s.section_name for s in jung)
        assert has_paragraph_range, "Jung sections should use paragraph-group chunking"

    def test_jung_shorthand_is_jung_pu(self) -> None:
        from corpus_inference_query.indexer import build_index
        sections = build_index(FIXTURE_CORPUS)
        jung = [s for s in sections if s.corpus_id == "jung-psychology-unconscious"]
        for s in jung:
            assert s.shorthand == "Jung-PU"

    def test_jung_listed_in_corpora(self) -> None:
        from corpus_inference_query.server import list_corpora
        result = list_corpora()
        assert "Jung-PU" in result
        assert "Carl Jung" in result


class TestConceptToolsWithJung:
    def test_explore_shadow_finds_jung(self) -> None:
        from corpus_inference_query.server import explore_concept
        result = explore_concept("shadow", corpus="Jung-PU")
        assert "shadow" in result.lower()

    def test_explore_individuation_finds_jung(self) -> None:
        from corpus_inference_query.server import explore_concept
        result = explore_concept("individuation", corpus="Jung-PU")
        assert "individuation" in result.lower()

    def test_explore_archetypes_finds_jung(self) -> None:
        from corpus_inference_query.server import explore_concept
        result = explore_concept("archetypes", corpus="Jung-PU")
        assert "archetype" in result.lower()

    def test_explore_dream_work_finds_jung(self) -> None:
        from corpus_inference_query.server import explore_concept
        result = explore_concept("dream_work", corpus="Jung-PU")
        assert "dream" in result.lower()

    def test_explore_collective_unconscious_finds_jung(self) -> None:
        from corpus_inference_query.server import explore_concept
        result = explore_concept("collective_unconscious", corpus="Jung-PU")
        assert "collective" in result.lower() or "unconscious" in result.lower()

    def test_concept_connections_shadow_individuation(self) -> None:
        from corpus_inference_query.server import concept_connections
        result = concept_connections("shadow", "individuation")
        assert len(result) > 0

    def test_explore_concept_no_corpus_filter(self) -> None:
        from corpus_inference_query.server import explore_concept
        result = explore_concept("shadow")
        assert len(result) > 0

    def test_query_jung_by_corpus_filter(self) -> None:
        from corpus_inference_query.server import query
        result = query("persona mask social role", corpus="Jung-PU")
        assert "Jung-PU" in result
