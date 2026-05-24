"""Tests for paragraph-group chunking."""
from __future__ import annotations

from corpus_inference_query.chunker import Chunk, chunk_paragraphs


class TestChunkParagraphs:
    def test_single_short_paragraph(self) -> None:
        result = chunk_paragraphs("Hello world.", target_tokens=100)
        assert len(result) == 1
        assert result[0].text == "Hello world."
        assert result[0].index == 0

    def test_groups_paragraphs_to_target(self) -> None:
        paras = "\n\n".join([f"Paragraph {i} with some content." for i in range(6)])
        result = chunk_paragraphs(paras, target_tokens=30, max_tokens=60, overlap_tokens=0)
        assert len(result) >= 2
        for chunk in result:
            assert isinstance(chunk, Chunk)

    def test_splits_oversized_paragraph(self) -> None:
        long = ". ".join(["This is sentence number " + str(i) for i in range(50)])
        result = chunk_paragraphs(long, target_tokens=20, max_tokens=40, overlap_tokens=0)
        assert len(result) >= 2

    def test_overlap_applied(self) -> None:
        paras = "First paragraph content.\n\nSecond paragraph content.\n\nThird paragraph content."
        result = chunk_paragraphs(paras, target_tokens=5, max_tokens=100, overlap_tokens=2)
        if len(result) > 1:
            assert "First" in result[1].text or len(result[1].text) > len("Second paragraph content.")

    def test_empty_text(self) -> None:
        result = chunk_paragraphs("")
        assert result == []
