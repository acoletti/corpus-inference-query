"""Tests for domain-concept vocabulary."""
from __future__ import annotations

from corpus_inference_query.concepts import (
    CONCEPT_KEYWORDS,
    concept_search_query,
)


def test_all_concepts_have_keywords() -> None:
    assert len(CONCEPT_KEYWORDS) == 10
    for concept, keywords in CONCEPT_KEYWORDS.items():
        assert len(keywords) >= 3, f"{concept} has too few keywords"


def test_concept_search_query_known() -> None:
    q = concept_search_query("shadow")
    assert "shadow" in q
    assert "dark side" in q


def test_concept_search_query_unknown() -> None:
    q = concept_search_query("unknown_concept")
    assert q == "unknown_concept"
