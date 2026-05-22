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


def _word_stem(word: str) -> str:
    """Simple stemming by removing common suffixes for cohesion matching."""
    w = word.lower()
    # Remove common suffixes (longest first to avoid incorrect matches)
    for suffix in ['tion', 'ing', 'ness', 'ure', 'ed', 'ly', 'es', 's']:
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            return w[:-len(suffix)]
    return w


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
# Module-level constants for §1–§4 detectors
# ---------------------------------------------------------------------------

_RELATIVE_CLAUSE_RE = re.compile(r'\b(which|who|that|whom|whose)\b', re.I)

_WORDY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bin the event that\b', re.I), 'if'),
    (re.compile(r'\bdue to the fact that\b', re.I), 'because'),
    (re.compile(r'\bat this point in time\b', re.I), 'now'),
    (re.compile(r'\bin order to\b', re.I), 'to'),
    (re.compile(r'\bvery unique\b', re.I), 'unique'),
    (re.compile(r'\bcompletely finished\b', re.I), 'finished'),
    (re.compile(r'\bfinal outcome\b', re.I), 'outcome'),
    (re.compile(r'\bfuture plans\b', re.I), 'plans'),
    (re.compile(r'\bpast history\b', re.I), 'history'),
    (re.compile(r'\brefer back\b', re.I), 'refer'),
    (re.compile(r'\bend result\b', re.I), 'result'),
    (re.compile(r'\bbasic fundamentals\b', re.I), 'fundamentals'),
]

_PASSIVE_RE = re.compile(r'\b(was|were|is|are|am|been|be)\s+\w+(?:ed|en)\b', re.I)
_ABSTRACT_NOUN_RE = re.compile(r'\b\w+(?:tion|ness|ment|ity|ism|ance|ence)\b', re.I)

# Constants for §5–§8 detectors
_CASUAL_MARKERS = frozenset(['kinda', 'gonna', 'wanna', 'gotta', 'awesome', 'totally', 'literally', 'basically'])
_FORMAL_TYPES = frozenset(['technical-doc', 'rfc', 'white-paper', 'memo', 'letter', 'cover-letter'])

_FK_RANGES: dict[str, tuple[float, float]] = {
    "email": (55.0, 85.0),
    "letter": (55.0, 85.0),
    "newsletter": (55.0, 85.0),
    "blog-post": (55.0, 85.0),
    "regular-blog": (55.0, 85.0),
    "technical-doc": (25.0, 60.0),
    "rfc": (25.0, 60.0),
    "readme": (25.0, 60.0),
    "white-paper": (25.0, 60.0),
    "memo": (40.0, 70.0),
    "speech": (65.0, 95.0),
    "talk-transcript": (65.0, 95.0),
    "op-ed": (45.0, 75.0),
    "article": (45.0, 75.0),
    "essay": (40.0, 70.0),
}

_HEDGE_WORDS = ['seems', 'appears', 'arguably', 'perhaps', 'possibly', 'might', 'could', 'may']
_INTENSIFIER_PATTERNS = [
    re.compile(r'\bobviously\b', re.I),
    re.compile(r'\bclearly\b', re.I),
    re.compile(r'\bcertainly\b', re.I),
    re.compile(r'\beveryone knows\b', re.I),
    re.compile(r'\bit is clear\b', re.I),
    re.compile(r'\bneedless to say\b', re.I),
]


# ---------------------------------------------------------------------------
# Universal rules §1–§15 (stubs — filled in Tasks 3–6)
# ---------------------------------------------------------------------------

def detect_clarity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    for sent in _split_sentences(text):
        words = sent.split()
        relative_clauses = len(_RELATIVE_CLAUSE_RE.findall(sent))
        if len(words) > 40 or relative_clauses > 2:
            violations.append(Violation(
                rule_id="§1",
                rule_title="Clarity",
                severity="warning",
                snippet=sent[:120],
            ))
    return violations


def detect_cohesion(text: str, types: list[str] | None = None) -> list[Violation] | None:
    sentences = _split_sentences(text)
    if len(sentences) < 2:
        return []
    violations = []
    for i in range(1, len(sentences)):
        prev_words = _content_words(sentences[i - 1])
        curr_words = _content_words(sentences[i])
        prev_stems = {_word_stem(w) for w in prev_words}
        curr_stems = {_word_stem(w) for w in curr_words}
        if prev_stems and curr_stems and not (prev_stems & curr_stems):
            violations.append(Violation(
                rule_id="§2",
                rule_title="Cohesion",
                severity="info",
                snippet=sentences[i][:120],
            ))
    return violations


def detect_concision(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    for pattern, suggestion in _WORDY_PATTERNS:
        for m in pattern.finditer(text):
            violations.append(Violation(
                rule_id="§3",
                rule_title="Concision",
                severity="warning",
                snippet=f'"{m.group()}" → "{suggestion}"',
                span=(m.start(), m.end()),
            ))
    return violations


def detect_voice_agency(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    violations = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        # Check passive voice if we have multiple sentences
        if len(sentences) >= 2:
            passive_count = sum(1 for s in sentences if _PASSIVE_RE.search(s))
            if passive_count / len(sentences) > 0.25:
                violations.append(Violation(
                    rule_id="§4",
                    rule_title="Voice and Agency",
                    severity="warning",
                    snippet=para[:120],
                ))
                continue
        # Check nominalization density (works for any text)
        content = _content_words(para)
        if content:
            nom_count = len(_ABSTRACT_NOUN_RE.findall(para))
            if nom_count / len(content) > 0.20:
                violations.append(Violation(
                    rule_id="§4",
                    rule_title="Voice and Agency",
                    severity="warning",
                    snippet=para[:120],
                ))
    return violations


def detect_diction_register(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if not types or not any(t in _FORMAL_TYPES for t in types):
        return []
    words_lower = set(w.lower().strip('.,!?;:()"\'') for w in text.split())
    found = words_lower & _CASUAL_MARKERS
    if not found:
        return []
    return [Violation(
        rule_id="§5",
        rule_title="Diction and Register",
        severity="warning",
        snippet=f"Casual marker(s) in formal context: {', '.join(sorted(found))}",
    )]


def detect_sentence_rhythm(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()] or [text]
    violations = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        if len(sentences) < 3:
            continue
        lengths = [len(s.split()) for s in sentences]
        try:
            std_dev = statistics.stdev(lengths)
        except statistics.StatisticsError:
            continue
        if std_dev < 3:
            violations.append(Violation(
                rule_id="§6",
                rule_title="Sentence Rhythm",
                severity="info",
                snippet=para[:120],
            ))
    return violations


def detect_audience_fit(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if not types:
        return None  # skip: type_unknown
    matched = [(t, _FK_RANGES[t]) for t in types if t in _FK_RANGES]
    if not matched:
        return []
    fre = _flesch_reading_ease(text)
    violations = []
    for t, (lo, hi) in matched:
        if not (lo <= fre <= hi):
            violations.append(Violation(
                rule_id="§7",
                rule_title="Audience Fit",
                severity="info",
                snippet=f"Flesch Reading Ease {fre:.1f} (expected {lo:.0f}–{hi:.0f} for type '{t}')",
            ))
    return violations


def detect_argument_honesty(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    words = text.lower().split()

    # Check for hedge word clusters (3+ in 50-word windows)
    window_size = min(50, len(words)) if words else 0
    if window_size > 0:
        for i in range(len(words) - window_size + 1):
            window = words[i:i + window_size]
            count = sum(1 for w in window if w.strip('.,!?;:"\'') in _HEDGE_WORDS)
            if count >= 3:
                snippet = ' '.join(words[i:i + 12])
                violations.append(Violation(
                    rule_id="§8",
                    rule_title="Argument Honesty",
                    severity="warning",
                    snippet=snippet[:120],
                ))
                break

    # Check for intensifier patterns
    for pattern in _INTENSIFIER_PATTERNS:
        for m in pattern.finditer(text):
            violations.append(Violation(
                rule_id="§8",
                rule_title="Argument Honesty",
                severity="warning",
                snippet=f'"{m.group()}" — unsupported intensifier',
                span=(m.start(), m.end()),
            ))
    return violations


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
