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

# Constants for §9–§12 detectors
_LAZY_CLOSERS = frozenset(["etc", "and so on", "and so forth", "among others"])

# Constants for §14 detector
_TRANSITION_WORDS = frozenset({
    "however", "therefore", "thus", "moreover", "furthermore", "nevertheless",
    "consequently", "meanwhile", "additionally", "finally", "first", "second",
    "third", "next", "then", "also", "but", "yet", "so", "still", "instead",
    "otherwise", "indeed", "notably", "similarly", "conversely",
})
_LEDE_TYPES = frozenset(["article", "essay", "op-ed", "blog-post", "newsletter"])
_FORMAL_TYPES = frozenset(['technical-doc', 'rfc', 'white-paper', 'memo', 'letter', 'cover-letter'])

_FK_RANGES: dict[str, tuple[float, float]] = {
    "email": (60.0, 80.0),
    "letter": (60.0, 80.0),
    "newsletter": (60.0, 80.0),
    "blog-post": (60.0, 80.0),
    "regular-blog": (60.0, 80.0),  # alias for blog-post
    "technical-doc": (30.0, 60.0),
    "rfc": (30.0, 60.0),
    "readme": (30.0, 60.0),
    "white-paper": (30.0, 60.0),
    "memo": (40.0, 70.0),
    "speech": (70.0, 90.0),
    "talk-transcript": (70.0, 90.0),
    "op-ed": (50.0, 70.0),
    "article": (50.0, 70.0),
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
    violations = []
    for sent in _split_sentences(text):
        for word in sent.split():
            if word.lower().strip('.,!?;:()"\'') in _CASUAL_MARKERS:
                violations.append(Violation(
                    rule_id="§5",
                    rule_title="Diction and Register",
                    severity="warning",
                    snippet=sent[:120],
                ))
                break  # one violation per sentence
    return violations


def detect_sentence_rhythm(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()] or [text]
    violations = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        if len(sentences) < 3:
            continue
        lengths = [len(s.split()) for s in sentences]
        std_dev = statistics.stdev(lengths)
        if std_dev < 3:
            violations.append(Violation(
                rule_id="§6",
                rule_title="Sentence Rhythm",
                severity="info",
                snippet=sentences[0][:120],
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
                snippet=text[:80],
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
    sentences = _split_sentences(text)
    if not sentences:
        return []
    first = sentences[0]
    parts = first.split()
    if not parts:
        return []
    first_word = parts[0].lower()
    # flag self-centered openers and dangling-relativizer openers
    if first_word in ("i", "my") or first_word in {"which", "who", "that", "whom", "whose"}:
        return [Violation(
            rule_id="§9",
            rule_title="Opening Craft",
            severity="warning",
            snippet=first,
        )]
    return []


def detect_closing_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    sentences = _split_sentences(text)
    if not sentences:
        return []
    last = sentences[-1]
    last_normalized = last.rstrip('.,!? ').lower()
    if any(last_normalized.endswith(c) for c in _LAZY_CLOSERS):
        return [Violation(
            rule_id="§10",
            rule_title="Closing Craft",
            severity="info",
            snippet=last[:120],
        )]
    if len(last.split()) < 4:
        return [Violation(
            rule_id="§10",
            rule_title="Closing Craft",
            severity="info",
            snippet=last,
        )]
    return []


def detect_concrete_abstract(text: str, types: list[str] | None = None) -> list[Violation] | None:
    words = text.split()
    total_words = len(words)
    if total_words < 30:
        return []
    # reuses §4's nominalization regex — same pattern, different threshold
    abstract_count = len(_ABSTRACT_NOUN_RE.findall(text))
    if abstract_count / total_words > 0.15:
        return [Violation(
            rule_id="§11",
            rule_title="Concrete vs. Abstract",
            severity="warning",
            snippet=text[:80],
        )]
    return []


def detect_style_consciousness(text: str, types: list[str] | None = None) -> list[Violation] | None:
    sentences = _split_sentences(text)
    if len(sentences) < 2:
        return []
    violations = []
    for i in range(len(sentences) - 1):
        words_curr = sentences[i].split()
        words_next = sentences[i + 1].split()
        if not words_curr or not words_next:
            continue
        if words_curr[0].lower() == words_next[0].lower():
            violations.append(Violation(
                rule_id="§12",
                rule_title="Style Consciousness",
                severity="info",
                snippet=sentences[i + 1][:120],
            ))
    return violations


def detect_voice_fidelity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    # Permanent skip: requires personal corpus vector search not available at detection time.
    return None


def detect_transitions(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 2:
        return []
    violations = []
    for i in range(len(paragraphs) - 1):
        curr_sents = _split_sentences(paragraphs[i])
        last_sent = curr_sents[-1] if curr_sents else ""
        next_sents = _split_sentences(paragraphs[i + 1])
        first_sent = next_sents[0] if next_sents else ""
        if not last_sent or not first_sent:
            continue
        prev_stems = {_word_stem(w) for w in _content_words(last_sent)}
        curr_stems = {_word_stem(w) for w in _content_words(first_sent)}
        if prev_stems & curr_stems:
            continue
        opening_word = first_sent.split()[0].lower().strip('.,!?;:()"\'') if first_sent.split() else ""
        if opening_word in _TRANSITION_WORDS:
            continue
        violations.append(Violation(
            rule_id="§14",
            rule_title="Transitions",
            severity="info",
            snippet=first_sent[:120],
        ))
    return violations


def detect_lede_and_title(text: str, types: list[str] | None = None) -> list[Violation] | None:
    # types=None applies rule (no type context → treat as generic prose)
    if types is not None and not any(t in _LEDE_TYPES for t in types):
        return []
    sentences = _split_sentences(text)
    if not sentences:
        return []
    first = sentences[0]
    violations = []
    if len(first.split()) > 35:
        violations.append(Violation(
            rule_id="§15",
            rule_title="Lede and Title",
            severity="warning",
            snippet=first[:120],
        ))
    if first.rstrip().endswith("?"):
        violations.append(Violation(
            rule_id="§15",
            rule_title="Lede and Title",
            severity="warning",
            snippet=first[:120],
        ))
    return violations


# ---------------------------------------------------------------------------
# Module-level constants for §A–§E type addenda
# ---------------------------------------------------------------------------

_ARTICLE_TYPES = frozenset(["article", "longform-journalism"])
_EMAIL_TYPES = frozenset(["email"])
_LETTER_TYPES = frozenset(["letter", "cover-letter"])
_TECH_DOC_TYPES = frozenset(["technical-doc", "readme", "rfc"])
_NEWSLETTER_TYPES = frozenset(["newsletter"])

_NUT_GRAF_MARKERS = re.compile(r'\b(this|here|today|in this)\b', re.I)
_MODAL_VERBS_RE = re.compile(r'\b(should|must|shall|may|can)\b', re.I)
_MARKDOWN_MARKERS = re.compile(r'(#{1,3} |`{1,3}|- |\* )')
_EMAIL_SOCIAL = frozenset(["please", "thank", "regards", "sincerely", "hi", "hello", "dear"])
_LETTER_CLOSINGS = frozenset(["sincerely", "regards", "yours", "best", "dear"])


# ---------------------------------------------------------------------------
# Type addenda §A–§J (§A–§E implemented; §F–§J stubs)
# ---------------------------------------------------------------------------

def detect_article(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if types is None or not any(t in _ARTICLE_TYPES for t in types):
        return []
    violations: list[Violation] = []
    word_count = len(text.split())
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 3 and word_count > 200:
        violations.append(Violation(
            rule_id="§A",
            rule_title="Article",
            severity="warning",
            snippet=text[:80],
        ))
    if word_count > 150:
        first_sentences = _split_sentences(text)[:3]
        has_nut_graf = any(_NUT_GRAF_MARKERS.search(s) for s in first_sentences)
        if not has_nut_graf:
            first_sent = first_sentences[0] if first_sentences else text
            violations.append(Violation(
                rule_id="§A",
                rule_title="Article",
                severity="info",
                snippet=first_sent[:120],
            ))
    return violations


def detect_email(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if types is None or not any(t in _EMAIL_TYPES for t in types):
        return []
    violations: list[Violation] = []
    word_count = len(text.split())
    if word_count > 150:
        violations.append(Violation(
            rule_id="§B",
            rule_title="Email",
            severity="info",
            snippet=text[:80],
        ))
    text_lower = text.lower()
    if not any(marker in text_lower for marker in _EMAIL_SOCIAL):
        violations.append(Violation(
            rule_id="§B",
            rule_title="Email",
            severity="info",
            snippet=text[:80],
        ))
    return violations


def detect_letter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if types is None or not any(t in _LETTER_TYPES for t in types):
        return []
    violations: list[Violation] = []
    word_count = len(text.split())
    if word_count < 50:
        violations.append(Violation(
            rule_id="§C",
            rule_title="Letter",
            severity="info",
            snippet=text[:80],
        ))
    text_lower = text.lower()
    if not any(marker in text_lower for marker in _LETTER_CLOSINGS):
        violations.append(Violation(
            rule_id="§C",
            rule_title="Letter",
            severity="info",
            snippet=text[:80],
        ))
    return violations


def detect_technical_doc(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if types is None or not any(t in _TECH_DOC_TYPES for t in types):
        return []
    violations: list[Violation] = []
    if not _MARKDOWN_MARKERS.search(text):
        violations.append(Violation(
            rule_id="§D",
            rule_title="Technical Doc",
            severity="warning",
            snippet=text[:80],
        ))
    word_count = len(text.split())
    if word_count > 200 and not _MODAL_VERBS_RE.search(text):
        violations.append(Violation(
            rule_id="§D",
            rule_title="Technical Doc",
            severity="info",
            snippet=text[:80],
        ))
    return violations


def detect_newsletter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if types is None or not any(t in _NEWSLETTER_TYPES for t in types):
        return []
    violations: list[Violation] = []
    word_count = len(text.split())
    if word_count > 400:
        violations.append(Violation(
            rule_id="§E",
            rule_title="Newsletter",
            severity="info",
            snippet=text[:80],
        ))
    elif word_count < 50:
        violations.append(Violation(
            rule_id="§E",
            rule_title="Newsletter",
            severity="info",
            snippet=text[:80],
        ))
    return violations


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
