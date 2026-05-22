"""Corpus manifest — maps shorthand IDs to file paths and section-detection patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CorpusSpec:
    corpus_id: str
    shorthand: str
    relative_path: str
    section_pattern: re.Pattern
    subsection_pattern: re.Pattern | None = None
    description: str = ""
    is_directory: bool = False
    style_tags: list[str] = field(default_factory=list)
    type_tags: list[str] = field(default_factory=list)


# Section heading patterns per corpus
CORPUS_SPECS: list[CorpusSpec] = [
    CorpusSpec(
        corpus_id="how-to-write-a-sentence",
        shorthand="HTWS",
        relative_path="references/fish-howtowriteasentence/",
        section_pattern=re.compile(r"^# (.+)$"),
        description="How to Write a Sentence — Stanley Fish (fixture stub)",
        is_directory=True,
        style_tags=["subordinating", "additive"],
        type_tags=["essay", "book"],
    ),
    CorpusSpec(
        corpus_id="strunk-elements-of-style",
        shorthand="Strunk",
        relative_path="references/strunk-elements-of-style/",
        section_pattern=re.compile(r"^# (.+)$"),
        description="Elements of Style — Strunk and White (fixture stub)",
        is_directory=True,
        style_tags=[],
        type_tags=["essay"],
    ),
]

SUBSECTION_BLOCKLIST = frozenset({
    "Table of Contents",
    "Note",
    "Tip",
    "Warning",
    "Image",
    "Introduction",
    "License",
})
