"""Corpus manifest — maps shorthand IDs to file paths and section-detection patterns."""

from __future__ import annotations

import re
import tomllib
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
    title: str = ""
    author: str = ""
    year: int = 0
    chunking_strategy: str = "heading"


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
        title="How to Write a Sentence",
        author="Stanley Fish",
        year=2011,
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
        title="Elements of Style",
        author="Strunk and White",
        year=1959,
    ),
    CorpusSpec(
        corpus_id="jung-psychology-unconscious",
        shorthand="Jung-PU",
        relative_path="references/jung-psychology-unconscious/",
        section_pattern=re.compile(r"^# (.+)$"),
        description="Psychology of the Unconscious — Carl Jung",
        is_directory=True,
        style_tags=["analytical"],
        type_tags=["psychology", "essay"],
        title="Psychology of the Unconscious",
        author="Carl Jung",
        year=1916,
        chunking_strategy="paragraph_group",
    ),
]


def load_corpus_specs(toml_path: Path) -> list[CorpusSpec]:
    """Load corpus specs from a corpus.toml file.

    Each [[source]] block in the TOML maps to one CorpusSpec.
    Returns an empty list if the file does not exist.
    """
    if not toml_path.exists():
        return []
    with toml_path.open("rb") as f:
        data = tomllib.load(f)
    specs = []
    for src in data.get("source", []):
        shorthand = src["shorthand"]
        corpus_id = src.get("id", shorthand.lower())
        specs.append(CorpusSpec(
            corpus_id=corpus_id,
            shorthand=shorthand,
            relative_path=src["path"],
            section_pattern=re.compile(r"^# (.+)$"),
            description=" — ".join(filter(None, [src.get("title", ""), src.get("author", "")])),
            is_directory=True,
            style_tags=list(src.get("default_style", [])),
            type_tags=list(src.get("default_type", [])),
            title=src.get("title", ""),
            author=src.get("author", ""),
            year=int(src.get("year", 0)),
            chunking_strategy=src.get("chunking_strategy", "heading"),
        ))
    return specs


SUBSECTION_BLOCKLIST = frozenset({
    "Table of Contents",
    "Note",
    "Tip",
    "Warning",
    "Image",
    "Introduction",
    "License",
})
