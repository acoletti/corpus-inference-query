"""Deterministic syllable-count meter checking for verse.

Built on the approximate vowel-group syllable counter in text_utils — no
dictionary or stress lookup, so this checks LINE LENGTH against a named
meter's expected syllable count, not stress placement. A line that passes
is *metrically plausible*; scansion (iamb vs. trochee) remains the
reviewer's judgment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .text_utils import count_syllables, split_words

# Named meters -> expected syllables per line. Feet counts follow the
# standard di-syllabic foot (iamb/trochee) or tri-syllabic foot
# (anapest/dactyl) arithmetic.
METERS: dict[str, int] = {
    "iambic_dimeter": 4,
    "iambic_trimeter": 6,
    "iambic_tetrameter": 8,
    "iambic_pentameter": 10,
    "iambic_hexameter": 12,
    "trochaic_tetrameter": 8,
    "trochaic_octameter": 16,
    "anapestic_tetrameter": 12,
    "dactylic_hexameter": 18,
    "common_meter": -1,  # alternating 8/6 — handled specially
}

_DEFAULT_TOLERANCE = 1


@dataclass
class LineScan:
    """Per-line syllable scan result."""

    line_number: int
    text: str
    syllables: int
    expected: int
    deviation: int  # syllables - expected


@dataclass
class MeterCheckResult:
    """Aggregate meter check across all non-empty lines."""

    meter: str
    expected_syllables: int
    tolerance: int
    line_count: int
    conforming_count: int
    lines: list[LineScan] = field(default_factory=list)

    @property
    def conformity_ratio(self) -> float:
        return self.conforming_count / self.line_count if self.line_count else 0.0


def _verse_lines(text: str) -> list[tuple[int, str]]:
    """Extract non-empty lines with 1-based line numbers, skipping scaffolding.

    Lines that are markdown headings, [AUTHOR: ...] placeholders, or blank
    are not verse and are excluded from the scan.
    """
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("[AUTHOR"):
            continue
        out.append((i, line))
    return out


def line_syllables(line: str) -> int:
    return sum(count_syllables(w) for w in split_words(line))


def check_meter(
    text: str,
    meter: str = "iambic_pentameter",
    tolerance: int = _DEFAULT_TOLERANCE,
) -> MeterCheckResult:
    """Scan each verse line's syllable count against the named meter.

    Raises ValueError for an unknown meter name. common_meter alternates
    expected counts 8/6 by verse-line position.
    """
    if meter not in METERS:
        raise ValueError(
            f"unknown meter '{meter}'; expected one of {sorted(METERS)}"
        )
    lines = _verse_lines(text)
    scans: list[LineScan] = []
    conforming = 0
    for pos, (line_number, line) in enumerate(lines):
        if meter == "common_meter":
            expected = 8 if pos % 2 == 0 else 6
        else:
            expected = METERS[meter]
        syllables = line_syllables(line)
        deviation = syllables - expected
        if abs(deviation) <= tolerance:
            conforming += 1
        scans.append(LineScan(line_number, line, syllables, expected, deviation))
    expected_display = METERS[meter] if meter != "common_meter" else 8
    return MeterCheckResult(
        meter=meter,
        expected_syllables=expected_display,
        tolerance=tolerance,
        line_count=len(scans),
        conforming_count=conforming,
        lines=scans,
    )
