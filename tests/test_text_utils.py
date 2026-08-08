"""Tests for text_utils splitting/counting helpers."""

from __future__ import annotations

from corpus_inference_query.text_utils import (
    count_syllables,
    split_paragraphs,
    split_sentences,
    split_words,
)


class TestSplitSentences:
    def test_splits_multiple_sentences(self) -> None:
        result = split_sentences("The cat sat. The dog ran! Did it work?")
        assert result == ["The cat sat.", "The dog ran!", "Did it work?"]

    def test_single_sentence(self) -> None:
        assert split_sentences("Just one sentence.") == ["Just one sentence."]

    def test_empty_text(self) -> None:
        assert split_sentences("") == []
        assert split_sentences("   ") == []


class TestSplitParagraphs:
    def test_splits_on_blank_lines(self) -> None:
        result = split_paragraphs("Para one.\n\nPara two.\n\n\nPara three.")
        assert result == ["Para one.", "Para two.", "Para three."]

    def test_single_paragraph(self) -> None:
        assert split_paragraphs("Just one paragraph.") == ["Just one paragraph."]

    def test_empty_text(self) -> None:
        assert split_paragraphs("") == []


class TestSplitWords:
    def test_extracts_words(self) -> None:
        assert split_words("The cat's hat, and the dog.") == [
            "The", "cat's", "hat", "and", "the", "dog",
        ]

    def test_empty_text(self) -> None:
        assert split_words("") == []


class TestCountSyllables:
    def test_single_syllable_word(self) -> None:
        assert count_syllables("cat") == 1

    def test_multi_syllable_word(self) -> None:
        assert count_syllables("elephant") == 3

    def test_silent_e(self) -> None:
        assert count_syllables("hope") == 1

    def test_empty_word(self) -> None:
        assert count_syllables("") == 0
