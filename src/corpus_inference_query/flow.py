"""Deterministic cadence/repetition scan for composed prose and verse.

Counts what a machine can count — opener runs, single-opener dominance,
repeated n-gram scaffolds, unit-length uniformity — and reports findings
for a cadence reviewer and repair loop to judge. Whether an anaphora is
compulsion or ceremony remains the reviewer's call; this scan only makes
the repetition visible.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, pstdev

from .text_utils import split_sentences, split_words

_TERMINAL_PUNCT = (".", "!", "?", ":", ";")

OPENER_RUN_THRESHOLD = 4
OPENER_RATIO_THRESHOLD = 0.5
NGRAM_REPEAT_THRESHOLD = 3
LENGTH_CV_THRESHOLD = 0.25
_MIN_UNITS_FOR_RATIOS = 6

FLOW_UNITS = ("auto", "lines", "sentences")


@dataclass
class FlowFinding:
    """One monotony marker with its category and evidence."""

    category: str  # opener_run | opener_dominance | repeated_ngram | uniform_length
    detail: str
    evidence: str


@dataclass
class FlowCheckResult:
    """Aggregate cadence scan across all units."""

    unit: str  # "lines" or "sentences"
    unit_count: int
    top_opener: str
    top_opener_ratio: float
    longest_opener_run: int
    length_cv: float
    findings: list[FlowFinding] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.unit_count == 0:
            return "empty"
        return "monotone" if self.findings else "varied"


def _scaffold_free_lines(text: str) -> list[str]:
    """Non-empty lines minus markdown headings and [AUTHOR: ...] placeholders."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("[AUTHOR"):
            continue
        out.append(line)
    return out


def _resolve_units(text: str, unit: str) -> tuple[str, list[str]]:
    """Resolve scan units: verse lines or prose sentences.

    Auto mode treats the text as verse when at least three scaffold-free
    lines exist and half or more lack terminal punctuation.
    """
    lines = _scaffold_free_lines(text)
    if unit == "lines":
        return "lines", lines
    if unit == "sentences":
        return "sentences", split_sentences("\n".join(lines))
    if len(lines) >= 3:
        unpunctuated = sum(1 for line in lines if not line.endswith(_TERMINAL_PUNCT))
        if unpunctuated * 2 >= len(lines):
            return "lines", lines
    return "sentences", split_sentences("\n".join(lines))


def _openers(units: list[str]) -> list[str]:
    out = []
    for u in units:
        words = split_words(u)
        if words:
            out.append(words[0].lower())
    return out


def _longest_run(openers: list[str]) -> tuple[str, int]:
    best_word, best_run, run = "", 0, 0
    prev = None
    for w in openers:
        run = run + 1 if w == prev else 1
        if run > best_run:
            best_word, best_run = w, run
        prev = w
    return best_word, best_run


def _repeated_trigrams(units: list[str]) -> list[tuple[str, int]]:
    counts: Counter[tuple[str, ...]] = Counter()
    for u in units:
        words = [w.lower() for w in split_words(u)]
        counts.update(tuple(words[i:i + 3]) for i in range(len(words) - 2))
    repeats = [(" ".join(g), n) for g, n in counts.items() if n >= NGRAM_REPEAT_THRESHOLD]
    repeats.sort(key=lambda p: (-p[1], p[0]))
    return repeats[:3]


def check_flow(text: str, unit: str = "auto") -> FlowCheckResult:
    """Scan units for opener monotony, repeated scaffolds, and flat lengths.

    Raises ValueError for an unknown unit. The uniform-length check runs
    only in sentence mode — in verse, line-length uniformity is the meter's
    job, so cadence variation must come from openers and syntax instead.
    """
    if unit not in FLOW_UNITS:
        raise ValueError(f"unknown unit '{unit}'; expected one of {list(FLOW_UNITS)}")
    unit_kind, units = _resolve_units(text, unit)
    openers = _openers(units)
    if not openers:
        return FlowCheckResult(unit_kind, 0, "", 0.0, 0, 0.0)

    counts = Counter(openers)
    top_opener, top_count = counts.most_common(1)[0]
    top_ratio = top_count / len(openers)
    run_word, run_len = _longest_run(openers)
    lengths = [len(split_words(u)) for u in units]
    cv = pstdev(lengths) / mean(lengths) if len(lengths) > 1 and mean(lengths) else 0.0

    findings: list[FlowFinding] = []
    if run_len >= OPENER_RUN_THRESHOLD:
        findings.append(FlowFinding(
            "opener_run",
            f"{run_len} consecutive units open with '{run_word}'",
            run_word))
    if len(openers) >= _MIN_UNITS_FOR_RATIOS and top_ratio >= OPENER_RATIO_THRESHOLD:
        findings.append(FlowFinding(
            "opener_dominance",
            f"'{top_opener}' opens {top_count}/{len(openers)} units ({top_ratio:.0%})",
            top_opener))
    for gram, n in _repeated_trigrams(units):
        findings.append(FlowFinding(
            "repeated_ngram", f"phrase scaffold repeats {n}x", gram))
    if unit_kind == "sentences" and len(units) >= _MIN_UNITS_FOR_RATIOS and cv < LENGTH_CV_THRESHOLD:
        findings.append(FlowFinding(
            "uniform_length",
            f"sentence lengths nearly uniform (CV {cv:.2f} < {LENGTH_CV_THRESHOLD})",
            f"mean {mean(lengths):.0f} words"))

    return FlowCheckResult(
        unit=unit_kind,
        unit_count=len(units),
        top_opener=top_opener,
        top_opener_ratio=round(top_ratio, 3),
        longest_opener_run=run_len,
        length_cv=round(cv, 3),
        findings=findings,
    )
