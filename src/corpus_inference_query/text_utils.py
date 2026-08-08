"""Shared text-splitting and counting helpers used by detectors and CorpusRepository."""

from __future__ import annotations

import re

# Sentence boundary: end punctuation followed by whitespace then a capital,
# digit, or quote — same heuristic corpus_repository.suggest_opening relied on.
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_PARAGRAPH_BOUNDARY_RE = re.compile(r"\n\s*\n")
_WORD_RE = re.compile(r"[A-Za-z']+")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)

SUBORDINATOR_MARKERS = {"which", "that", "who", "because", "although", "while"}
TRANSITION_WORDS = {
    "however", "therefore", "moreover", "furthermore", "meanwhile", "consequently",
}
HEDGE_PHRASES = [
    "perhaps", "arguably", "some might say", "it could be argued", "it could be said",
    "one could argue",
]
INTENSIFIERS = {"clearly", "obviously", "undeniably"}
REDUNDANT_PHRASES = [
    "each and every", "past history", "true fact", "end result", "final outcome",
    "close proximity", "advance planning", "basic fundamentals", "completely eliminate",
    "very unique", "actual fact", "future plans", "unexpected surprise", "free gift",
    "added bonus",
]
ABSTRACT_SUFFIXES = ("tion", "sion", "ism", "ity", "ness", "ance", "ence")
REQUEST_MARKERS = ["please", "could you", "can you", "let me know"]

# Structural-marker regexes shared by type inference (registry.py) and the
# type-addenda detectors (§B, §C, §D, §E, §I) in detectors/rules.py.
SALUTATION_RE = re.compile(r"^\s*(Dear|Hi|Hello)\b", re.IGNORECASE)
SIGNOFF_RE = re.compile(r"\b(Sincerely|Regards|Best,|Yours truly)\b", re.IGNORECASE)
MEMO_HEADER_RE = re.compile(r"^\s*(TO|FROM|RE)\s*:", re.MULTILINE)
SUBJECT_LINE_RE = re.compile(r"^\s*Subject\s*:", re.MULTILINE | re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"^#{1,3}\s", re.MULTILINE)
NUMBERED_SECTION_RE = re.compile(r"^\d+\.\s", re.MULTILINE)
MARKDOWN_LINK_RE = re.compile(r"\[.*?\]\(.*?\)")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using an end-punctuation + capital-start heuristic."""
    stripped = text.strip()
    if not stripped:
        return []
    return [s.strip() for s in _SENTENCE_BOUNDARY_RE.split(stripped) if s.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on blank lines."""
    stripped = text.strip()
    if not stripped:
        return []
    return [p.strip() for p in _PARAGRAPH_BOUNDARY_RE.split(stripped) if p.strip()]


def split_words(text: str) -> list[str]:
    """Extract alphabetic word tokens (contractions kept intact)."""
    return _WORD_RE.findall(text)


def count_syllables(word: str) -> int:
    """Approximate syllable count via vowel-group counting (no dictionary lookup)."""
    lowered = word.lower().strip("'")
    if not lowered:
        return 0
    groups = _VOWEL_GROUP_RE.findall(lowered)
    count = len(groups)
    if lowered.endswith("e") and not lowered.endswith("le") and count > 1:
        count -= 1
    return max(count, 1)
