"""One detector function per writing-standards rule.

Each function has signature ``(text, repo, types) -> RuleViolation | SkippedRule | None``.
``types`` is the resolved type list (explicit or inferred) — most detectors ignore it;
§7 and §15 use it to decide applicability. Returning ``None`` means the rule passed.
Each detector returns at most one violation (the first offending instance found),
matching the one-entry-per-rule response shape.
See ``standards/writing-standards.md`` for the human-readable rule descriptions this
mirrors, and ``docs/superpowers/plans/`` for the v1 heuristic-simplification rationale.
"""

from __future__ import annotations

import re
import statistics
from itertools import pairwise
from typing import TYPE_CHECKING

from ..text_utils import (
    ABSTRACT_SUFFIXES,
    HEDGE_PHRASES,
    INTENSIFIERS,
    MARKDOWN_HEADING_RE,
    MARKDOWN_LINK_RE,
    MEMO_HEADER_RE,
    NUMBERED_SECTION_RE,
    REDUNDANT_PHRASES,
    REQUEST_MARKERS,
    SALUTATION_RE,
    SUBORDINATOR_MARKERS,
    TRANSITION_WORDS,
    count_syllables,
    split_paragraphs,
    split_sentences,
    split_words,
)
from .types import RuleViolation, SkippedRule

if TYPE_CHECKING:
    from ..corpus_repository import CorpusRepository

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "it", "this", "that", "as", "at", "by", "from",
    "be", "been", "has", "have", "had",
}
_PASSIVE_RE = re.compile(r"\b(is|are|was|were|be|been|being)\s+\w+(ed|en)\b", re.IGNORECASE)
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,5}\b")
_TERMINAL_PUNCTUATION = ".!?\"'"
_FIRST_HEADING_RE = re.compile(r"^#{1,3}\s*(.+)$", re.MULTILINE)

# type name -> (min_grade, max_grade) acceptable Flesch-Kincaid band, used by §7.
AUDIENCE_BANDS: dict[str, tuple[float, float]] = {
    "email": (6, 10),
    "technical_doc": (10, 16),
    "blog": (6, 10),
    "article": (8, 12),
    "memo": (8, 12),
    "letter": (6, 10),
    "newsletter": (6, 10),
    "op_ed": (9, 13),
    "white_paper": (10, 16),
    "speech": (6, 10),
}
# type names §15 (lede/title craft) treats as article-like.
_ARTICLE_LIKE_TYPES = {"article", "op_ed", "blog", "newsletter"}


def _exemplar(
    repo: CorpusRepository,
    style: list[str] | None = None,
    type_filter: list[str] | None = None,
    corpus: str | None = None,
) -> tuple[str | None, str | None]:
    section = repo.find_exemplar_section(style=style, type_filter=type_filter, corpus=corpus)
    if section is None:
        return None, None
    return section.citation, section.content


def _span_for(text: str, needle: str) -> tuple[int, int] | None:
    start = text.find(needle)
    return (start, start + len(needle)) if start >= 0 else None


def check_s1_clarity(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """>40 words in one sentence, or >=3 subordinator markers in one sentence."""
    for sentence in split_sentences(text):
        words = split_words(sentence)
        subordinators = sum(1 for w in words if w.lower() in SUBORDINATOR_MARKERS)
        if len(words) > 40 or subordinators >= 3:
            citation, rewrite = _exemplar(repo, type_filter=["essay"])
            return RuleViolation(
                rule_id="§1",
                rule_title="Clarity (one-pass reading)",
                severity="warning",
                span=_span_for(text, sentence),
                snippet=sentence[:120],
                exemplar_citation=citation,
                suggested_rewrite_from_exemplar=rewrite,
            )
    return None


def check_s2_cohesion(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """>50% of adjacent sentence pairs in a paragraph share zero repeated content words."""
    broken = 0
    total = 0
    for para in split_paragraphs(text):
        sentences = split_sentences(para)
        for a, b in pairwise(sentences):
            total += 1
            words_a = {w.lower() for w in split_words(a) if w.lower() not in _STOPWORDS}
            words_b = {w.lower() for w in split_words(b) if w.lower() not in _STOPWORDS}
            if not (words_a & words_b):
                broken += 1
    if total >= 2 and broken / total > 0.5:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§2",
            rule_title="Cohesion (old to new)",
            severity="info",
            span=None,
            snippet=f"{broken}/{total} adjacent sentence pairs share no repeated words",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s3_concision(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Text contains a curated redundant phrase (Strunk-style "needless words")."""
    lowered = text.lower()
    for phrase in REDUNDANT_PHRASES:
        idx = lowered.find(phrase)
        if idx >= 0:
            citation, rewrite = _exemplar(repo, corpus="Strunk")
            if citation is None:
                citation, rewrite = _exemplar(repo, type_filter=["essay"])
            return RuleViolation(
                rule_id="§3",
                rule_title="Concision",
                severity="warning",
                span=(idx, idx + len(phrase)),
                snippet=text[idx : idx + len(phrase)],
                exemplar_citation=citation,
                suggested_rewrite_from_exemplar=rewrite,
            )
    return None


def check_s4_voice(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Passive-construction rate (regex-approximated) exceeds 25% of sentences."""
    sentences = split_sentences(text)
    if not sentences:
        return None
    passive_count = sum(1 for s in sentences if _PASSIVE_RE.search(s))
    rate = passive_count / len(sentences)
    if rate > 0.25:
        citation, rewrite = _exemplar(repo, style=["subordinating"])
        return RuleViolation(
            rule_id="§4",
            rule_title="Voice / agency",
            severity="warning",
            span=None,
            snippet=f"passive-construction rate {rate:.0%} across {len(sentences)} sentences",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s5_diction(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """First all-caps acronym (2-5 letters) with no parenthetical gloss within 40 chars."""
    seen: set[str] = set()
    for m in _ACRONYM_RE.finditer(text):
        acronym = m.group(0)
        if acronym in seen:
            continue
        seen.add(acronym)
        window = text[m.end() : m.end() + 40]
        if "(" not in window:
            citation, rewrite = _exemplar(repo, type_filter=["essay"])
            return RuleViolation(
                rule_id="§5",
                rule_title="Diction and register",
                severity="info",
                span=(m.start(), m.end()),
                snippet=acronym,
                exemplar_citation=citation,
                suggested_rewrite_from_exemplar=rewrite,
            )
    return None


def _flesch_kincaid_grade(text: str) -> float | None:
    sentences = split_sentences(text)
    words = split_words(text)
    if not sentences or not words:
        return None
    syllables = sum(count_syllables(w) for w in words)
    return 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59


def check_s6_rhythm(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Population stdev of sentence word-counts <2 (monotonous) or >15 (erratic)."""
    sentences = split_sentences(text)
    if len(sentences) < 5:
        return None
    lengths = [len(split_words(s)) for s in sentences]
    spread = statistics.pstdev(lengths)
    if spread < 2 or spread > 15:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§6",
            rule_title="Sentence rhythm",
            severity="info",
            span=None,
            snippet=f"sentence-length stdev {spread:.1f} across {len(sentences)} sentences",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s7_audience_fit(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Approx. Flesch-Kincaid grade outside the resolved type's expected band."""
    band_type = next((t for t in types if t in AUDIENCE_BANDS), None)
    if band_type is None:
        return SkippedRule(rule_id="§7", reason_code="type_unknown")
    grade = _flesch_kincaid_grade(text)
    if grade is None:
        return SkippedRule(rule_id="§7", reason_code="type_unknown")
    low, high = AUDIENCE_BANDS[band_type]
    if grade < low or grade > high:
        citation, rewrite = _exemplar(repo, type_filter=[band_type])
        return RuleViolation(
            rule_id="§7",
            rule_title="Audience fit",
            severity="warning",
            span=None,
            snippet=f"approx. grade {grade:.1f} outside {low:g}-{high:g} band for type '{band_type}'",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s8_argument_honesty(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Hedge-phrase density >2 per 100 words, or >=3 unsupported intensifiers."""
    words = split_words(text)
    if not words:
        return None
    lowered = text.lower()
    hedge_count = sum(lowered.count(phrase) for phrase in HEDGE_PHRASES)
    intensifier_count = sum(1 for w in words if w.lower() in INTENSIFIERS)
    density = hedge_count / (len(words) / 100)
    if density > 2 or intensifier_count >= 3:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§8",
            rule_title="Argument honesty",
            severity="warning",
            span=None,
            snippet=f"{hedge_count} hedge phrase(s), {intensifier_count} unsupported intensifier(s)",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s9_opening(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """First sentence exceeds 25 words."""
    sentences = split_sentences(text)
    if not sentences:
        return None
    if len(split_words(sentences[0])) > 25:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§9",
            rule_title="Opening craft (angle of lean)",
            severity="warning",
            span=_span_for(text, sentences[0]),
            snippet=sentences[0][:120],
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s10_closing(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Text ends without terminal punctuation, or the closing sentence is <4 words."""
    stripped = text.strip()
    if not stripped:
        return None
    sentences = split_sentences(text)
    last = sentences[-1] if sentences else stripped
    no_terminal_punct = stripped[-1] not in _TERMINAL_PUNCTUATION
    too_short = len(split_words(last)) < 4
    if no_terminal_punct or too_short:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§10",
            rule_title="Closing craft",
            severity="info",
            span=_span_for(text, last),
            snippet=last[:120],
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s11_concrete(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Abstract-noun-suffix density (-tion/-ism/-ity/-ness/-ance/-ence) exceeds 8% of words."""
    words = split_words(text)
    if not words:
        return None
    abstract_count = sum(1 for w in words if w.lower().endswith(ABSTRACT_SUFFIXES))
    density = abstract_count / len(words)
    if density > 0.08:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§11",
            rule_title="Concrete over abstract",
            severity="warning",
            span=None,
            snippet=f"abstract-noun density {density:.0%} across {len(words)} words",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s12_style_consciousness(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Per-paragraph average sentence length swings by more than 20 words."""
    paragraphs = split_paragraphs(text)
    if len(paragraphs) < 2:
        return None
    averages = []
    for para in paragraphs:
        sentences = split_sentences(para)
        if not sentences:
            continue
        lengths = [len(split_words(s)) for s in sentences]
        averages.append(sum(lengths) / len(lengths))
    if len(averages) < 2:
        return None
    swing = max(averages) - min(averages)
    if swing > 20:
        citation, rewrite = _exemplar(repo, type_filter=["essay"])
        return RuleViolation(
            rule_id="§12",
            rule_title="Style consciousness",
            severity="info",
            span=None,
            snippet=f"per-paragraph avg sentence length swings by {swing:.1f} words",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s13_voice_fidelity(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Best similarity to the personal corpus is below 0.3; skips gracefully otherwise."""
    if not repo.has_corpus_sections("personal"):
        return SkippedRule(rule_id="§13", reason_code="personal_corpus_empty")
    score = repo.voice_similarity_score(text, corpus="personal")
    if score is None:
        return SkippedRule(rule_id="§13", reason_code="vector_backend_unavailable")
    if score < 0.3:
        citation, rewrite = _exemplar(repo, corpus="personal")
        return RuleViolation(
            rule_id="§13",
            rule_title="Voice fidelity",
            severity="warning",
            span=None,
            snippet=f"best similarity to personal corpus: {score:.2f}",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_s14_transitions(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """A non-first, multi-sentence paragraph uses zero transition words."""
    paragraphs = split_paragraphs(text)
    for para in paragraphs[1:]:
        sentences = split_sentences(para)
        if len(sentences) <= 1:
            continue
        words = {w.lower() for w in split_words(para)}
        if not (words & TRANSITION_WORDS):
            citation, rewrite = _exemplar(repo, type_filter=["essay"])
            return RuleViolation(
                rule_id="§14",
                rule_title="Transitions",
                severity="info",
                span=_span_for(text, para),
                snippet=para[:120],
                exemplar_citation=citation,
                suggested_rewrite_from_exemplar=rewrite,
            )
    return None


def check_s15_lede(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Article-like types only: first paragraph should be 2-5 sentences (nut-graf-size proxy)."""
    article_type = next((t for t in types if t in _ARTICLE_LIKE_TYPES), None)
    if article_type is None:
        return SkippedRule(rule_id="§15", reason_code="type_unknown")
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return None
    sentence_count = len(split_sentences(paragraphs[0]))
    if sentence_count < 2 or sentence_count > 5:
        citation, rewrite = _exemplar(repo, type_filter=[article_type])
        return RuleViolation(
            rule_id="§15",
            rule_title="Lede and title craft",
            severity="warning",
            span=None,
            snippet=f"first paragraph has {sentence_count} sentence(s)",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_a_article(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """First paragraph word count outside 20-80 (nut-graf-size proxy)."""
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return None
    word_count = len(split_words(paragraphs[0]))
    if word_count < 20 or word_count > 80:
        citation, rewrite = _exemplar(repo, type_filter=["article"])
        return RuleViolation(
            rule_id="§A",
            rule_title="Article",
            severity="warning",
            span=None,
            snippet=f"first paragraph has {word_count} words",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_b_email(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """First 2 sentences have no question mark and no explicit request marker."""
    sentences = split_sentences(text)
    opening = " ".join(sentences[:2]).lower()
    has_question = "?" in opening
    has_request = any(marker in opening for marker in REQUEST_MARKERS)
    if not has_question and not has_request:
        citation, rewrite = _exemplar(repo, type_filter=["email"])
        return RuleViolation(
            rule_id="§B",
            rule_title="Email",
            severity="warning",
            span=None,
            snippet=opening[:120] or "(empty)",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_c_letter(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """First non-blank line doesn't open with a salutation (Dear/Hi/Hello)."""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not SALUTATION_RE.match(first_line):
        citation, rewrite = _exemplar(repo, type_filter=["letter"])
        return RuleViolation(
            rule_id="§C",
            rule_title="Letter",
            severity="warning",
            span=None,
            snippet=first_line[:80] or "(empty)",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_d_technical_doc(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Fewer than 2 markdown headings or numbered-section markers."""
    heading_count = len(MARKDOWN_HEADING_RE.findall(text)) + len(
        NUMBERED_SECTION_RE.findall(text)
    )
    if heading_count < 2:
        citation, rewrite = _exemplar(repo, type_filter=["technical_doc"])
        return RuleViolation(
            rule_id="§D",
            rule_title="Technical doc / RFC",
            severity="warning",
            span=None,
            snippet=f"{heading_count} heading(s)/numbered section(s) found",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_e_newsletter(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Zero markdown links in the text (proxy for a missing link-as-citation/CTA)."""
    if not MARKDOWN_LINK_RE.search(text):
        citation, rewrite = _exemplar(repo, type_filter=["newsletter"])
        return RuleViolation(
            rule_id="§E",
            rule_title="Newsletter",
            severity="info",
            span=None,
            snippet="no markdown links found",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_f_oped(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Word count exceeds 1200."""
    word_count = len(split_words(text))
    if word_count > 1200:
        citation, rewrite = _exemplar(repo, type_filter=["op_ed"])
        return RuleViolation(
            rule_id="§F",
            rule_title="Op-ed",
            severity="warning",
            span=None,
            snippet=f"{word_count} words (limit 1200)",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_g_blog_post(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Words-per-heading ratio exceeds 600 (subheads too sparse)."""
    word_count = len(split_words(text))
    heading_count = len(MARKDOWN_HEADING_RE.findall(text))
    if word_count / max(heading_count, 1) > 600:
        citation, rewrite = _exemplar(repo, type_filter=["blog"])
        return RuleViolation(
            rule_id="§G",
            rule_title="Blog post",
            severity="info",
            span=None,
            snippet=f"{word_count} words across {heading_count} heading(s)",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_h_white_paper(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Long docs (>1500 words) with no "summary" keyword in the opening."""
    word_count = len(split_words(text))
    if word_count <= 1500:
        return None
    paragraphs = split_paragraphs(text)
    first_para = paragraphs[0] if paragraphs else ""
    has_summary = "summary" in first_para.lower()
    if not has_summary:
        first_heading = _FIRST_HEADING_RE.search(text)
        has_summary = bool(first_heading and "summary" in first_heading.group(1).lower())
    if not has_summary:
        citation, rewrite = _exemplar(repo, type_filter=["white_paper"])
        return RuleViolation(
            rule_id="§H",
            rule_title="White paper",
            severity="warning",
            span=None,
            snippet=f"{word_count} words, no 'summary' found in opening",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_i_memo(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """First 5 lines don't contain both a TO: and a FROM: header field."""
    joined = "\n".join(text.splitlines()[:5])
    fields = {m.group(1).upper() for m in MEMO_HEADER_RE.finditer(joined)}
    if not {"TO", "FROM"} <= fields:
        citation, rewrite = _exemplar(repo, type_filter=["memo"])
        return RuleViolation(
            rule_id="§I",
            rule_title="Memo",
            severity="warning",
            span=None,
            snippet=joined[:120],
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None


def check_j_speech(
    text: str, repo: CorpusRepository, types: list[str]
) -> RuleViolation | SkippedRule | None:
    """Median sentence word-count is 18 or more (too long for spoken delivery)."""
    sentences = split_sentences(text)
    if not sentences:
        return None
    lengths = [len(split_words(s)) for s in sentences]
    median_length = statistics.median(lengths)
    if median_length >= 18:
        citation, rewrite = _exemplar(repo, type_filter=["speech"])
        return RuleViolation(
            rule_id="§J",
            rule_title="Speech / talk",
            severity="info",
            span=None,
            snippet=f"median sentence length {median_length:.1f} words",
            exemplar_citation=citation,
            suggested_rewrite_from_exemplar=rewrite,
        )
    return None
