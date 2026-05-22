"""Writing-standards detectors — one function per §-rule."""
from __future__ import annotations

import re
import statistics

from .base import Violation

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SENT_END_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z\"\'])')
_STOP_WORDS = frozenset([
    'the', 'a', 'an', 'in', 'of', 'to', 'and', 'for', 'is', 'was',
    'are', 'it', 'this', 'that', 'with', 'by', 'at', 'be', 'as',
    'on', 'or', 'not', 'but', 'from', 'has', 'had', 'have', 'its',
])


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]


def _content_words(text: str) -> list[str]:
    return [
        w.lower().strip('.,!?;:()"\'')
        for w in text.split()
        if w.lower().strip('.,!?;:()"\'') not in _STOP_WORDS
    ]


def _count_syllables(word: str) -> int:
    word = word.lower().strip('.,!?;:()"\' ')
    if not word:
        return 0
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in 'aeiou'
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith('e') and count > 1:
        count -= 1
    return max(1, count)


def _flesch_reading_ease(text: str) -> float:
    sentences = _split_sentences(text)
    if not sentences:
        return 100.0
    words = text.split()
    if not words:
        return 100.0
    syllable_count = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = syllable_count / len(words)
    return 206.835 - 1.015 * asl - 84.6 * asw


# ---------------------------------------------------------------------------
# Universal rules §1–§15 (stubs — filled in Tasks 3–6)
# ---------------------------------------------------------------------------

def detect_clarity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_cohesion(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_concision(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_voice_agency(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_diction_register(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_sentence_rhythm(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_audience_fit(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_argument_honesty(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_opening_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_closing_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_concrete_abstract(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_style_consciousness(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_voice_fidelity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return None  # always skip in M3 — requires personal corpus vector search


def detect_transitions(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_lede_and_title(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


# ---------------------------------------------------------------------------
# Type addenda §A–§J (stubs — filled in Tasks 7–8)
# ---------------------------------------------------------------------------

def detect_article(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_email(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_letter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_technical_doc(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_newsletter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_op_ed(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_blog_post(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_white_paper(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_memo(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_speech(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []
