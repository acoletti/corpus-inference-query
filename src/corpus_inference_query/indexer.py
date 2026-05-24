"""Corpus loading, chunking, and section index builder."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .corpus_config import CORPUS_SPECS, SUBSECTION_BLOCKLIST, CorpusSpec, load_corpus_specs


@dataclass
class Section:
    corpus_id: str
    shorthand: str
    chapter: str
    section_name: str
    citation: str
    content: str
    line_start: int
    keywords: set[str] = field(default_factory=set)
    style_tags: list[str] = field(default_factory=list)
    type_tags: list[str] = field(default_factory=list)


@dataclass
class _ParserState:
    current_chapter: str = ""
    current_section_name: str = ""
    current_lines: list[str] = field(default_factory=list)
    current_start: int = 0
    subsection_count: int = 0


def _extract_keywords(text: str) -> set[str]:
    """Extract lowercase keywords from text for search indexing."""
    words = re.findall(r"[a-zA-Z_]\w{2,}", text)
    return {w.lower() for w in words}


def _is_blocked_subsection(name: str) -> bool:
    stripped = name.strip()
    if stripped in SUBSECTION_BLOCKLIST:
        return True
    if len(stripped) < 5 or len(stripped) > 100:
        return True
    if stripped.startswith(("http", ">>>", "...", "#", "```")):
        return True
    # Skip lines that are all-caps (likely headers/navigation)
    if stripped.isupper() and len(stripped) > 3:
        return True
    return False


def _flush_current_section(
    spec: CorpusSpec, state: _ParserState, sections: list[Section]
) -> None:
    if state.current_lines and state.current_section_name:
        content = "\n".join(state.current_lines).strip()
        if len(content) > 20:
            citation = f"{spec.shorthand} §{state.current_chapter}"
            if state.current_section_name != state.current_chapter:
                citation = f"{spec.shorthand} §{state.current_section_name}"
            kw = _extract_keywords(content)
            kw.update(_extract_keywords(state.current_section_name))
            kw.update(_extract_keywords(state.current_chapter))
            sections.append(
                Section(
                    corpus_id=spec.corpus_id,
                    shorthand=spec.shorthand,
                    chapter=state.current_chapter,
                    section_name=state.current_section_name,
                    citation=citation,
                    content=content,
                    line_start=state.current_start,
                    keywords=kw,
                )
            )


def _extract_heading(spec: CorpusSpec, groups: list[str]) -> tuple[str, str]:
    if spec.corpus_id == "google-coding-standards":
        chapter = groups[0] if groups else ""
        section_name = groups[1] if len(groups) > 1 else groups[0]
    elif spec.corpus_id == "clean-code-inference":
        chapter = f"Ch{groups[0]}" if groups else ""
        section_name = groups[1].strip() if len(groups) > 1 else groups[0].strip()
    else:
        chapter = groups[0].strip() if groups else ""
        section_name = groups[0].strip()
    return chapter, section_name


def _index_markdown_sections(
    spec: CorpusSpec, text: str
) -> list[Section]:
    """Index a markdown file by splitting on section/subsection headings."""
    lines = text.split("\n")
    sections: list[Section] = []
    state = _ParserState()

    for i, line in enumerate(lines):
        m = spec.section_pattern.match(line)
        if m:
            _flush_current_section(spec, state, sections)
            groups = [g for g in m.groups() if g]
            state.current_chapter, state.current_section_name = _extract_heading(
                spec, groups
            )
            state.current_lines = [line]
            state.current_start = i
            state.subsection_count = 0
            continue

        if spec.subsection_pattern:
            sm = spec.subsection_pattern.match(line)
            if sm and not _is_blocked_subsection(sm.group(1)):
                _flush_current_section(spec, state, sections)
                state.subsection_count += 1
                state.current_section_name = sm.group(1).strip()
                state.current_lines = [line]
                state.current_start = i
                continue

        state.current_lines.append(line)

    _flush_current_section(spec, state, sections)
    return sections


def _index_google_sections(spec: CorpusSpec, text: str) -> list[Section]:
    """Google style guide has clean numbered sections — use them directly."""
    return _index_markdown_sections(spec, text)


def _index_design_patterns(spec: CorpusSpec, base_path: Path) -> list[Section]:
    """Index design pattern files from src/PatternName/Conceptual/main.py."""
    sections: list[Section] = []
    src_dir = base_path / spec.relative_path
    if not src_dir.exists():
        return sections

    for pattern_dir in sorted(src_dir.iterdir()):
        if not pattern_dir.is_dir() or pattern_dir.name.startswith("."):
            continue
        pattern_name = pattern_dir.name
        # Find main.py files (may be nested under Conceptual/, ThreadSafe/, etc.)
        for main_py in pattern_dir.rglob("main.py"):
            content = main_py.read_text(errors="replace")
            variant = main_py.parent.name
            section_name = pattern_name
            if variant not in ("Conceptual", pattern_name):
                section_name = f"{pattern_name}/{variant}"
            citation = f"DP-Py §{section_name}"
            sections.append(Section(
                corpus_id=spec.corpus_id,
                shorthand=spec.shorthand,
                chapter=pattern_name,
                section_name=section_name,
                citation=citation,
                content=content,
                line_start=0,
                keywords=_extract_keywords(content) | {pattern_name.lower()},
            ))
    return sections


def _index_example_code(spec: CorpusSpec, base_path: Path) -> list[Section]:
    """Index Fluent Python 2e example .py files by chapter."""
    sections: list[Section] = []
    ex_dir = base_path / spec.relative_path
    if not ex_dir.exists():
        return sections

    for chapter_dir in sorted(ex_dir.iterdir()):
        if not chapter_dir.is_dir() or chapter_dir.name.startswith("."):
            continue
        chapter_name = chapter_dir.name
        for py_file in sorted(chapter_dir.rglob("*.py")):
            content = py_file.read_text(errors="replace")
            if len(content.strip()) < 10:
                continue
            rel = py_file.relative_to(ex_dir)
            citation = f"FP2e-ex §{rel}"
            sections.append(Section(
                corpus_id=spec.corpus_id,
                shorthand=spec.shorthand,
                chapter=chapter_name,
                section_name=str(rel),
                citation=citation,
                content=content,
                line_start=0,
                keywords=_extract_keywords(content) | {chapter_name.lower()},
            ))
    return sections


def _index_paragraph_groups(
    spec: CorpusSpec, text: str, source_name: str = "",
) -> list[Section]:
    """Index text using paragraph-group chunking for dense prose."""
    from .chunker import chunk_paragraphs  # noqa: PLC0415

    try:
        from .settings import get_settings  # noqa: PLC0415
        s = get_settings()
        target = s.chunk_target_tokens
        max_t = s.chunk_max_tokens
        overlap = s.chunk_overlap_tokens
    except ImportError:
        target, max_t, overlap = 512, 1024, 64

    chunks = chunk_paragraphs(text, target, max_t, overlap)
    sections: list[Section] = []
    for chunk in chunks:
        p_end = chunk.paragraph_start + chunk.paragraph_count - 1
        if source_name:
            name = f"{source_name} (p{chunk.paragraph_start}-{p_end})"
        else:
            name = f"p{chunk.paragraph_start}-{p_end}"
        citation = f"{spec.shorthand} §{name}"
        sections.append(Section(
            corpus_id=spec.corpus_id,
            shorthand=spec.shorthand,
            chapter=source_name,
            section_name=name,
            citation=citation,
            content=chunk.text,
            line_start=chunk.paragraph_start,
            keywords=_extract_keywords(chunk.text),
            style_tags=list(spec.style_tags),
            type_tags=list(spec.type_tags),
        ))
    return sections


def build_index(corpus_path: Path) -> list[Section]:
    """Build the full section index from all corpus files."""
    all_sections: list[Section] = []

    corpus_toml = corpus_path / "corpus.toml"
    specs = load_corpus_specs(corpus_toml) if corpus_toml.exists() else CORPUS_SPECS
    for spec in specs:
        if spec.is_directory:
            if spec.corpus_id == "design-patterns-python":
                all_sections.extend(_index_design_patterns(spec, corpus_path))
            elif spec.corpus_id == "example-code-2e":
                all_sections.extend(_index_example_code(spec, corpus_path))
            else:
                # Generic directory corpus: index every .md file under the
                # directory using the spec's section pattern.
                dir_path = corpus_path / spec.relative_path
                if dir_path.exists():
                    for md_file in sorted(dir_path.rglob("*.md")):
                        text = md_file.read_text(errors="replace")
                        if spec.chunking_strategy == "paragraph_group":
                            name = md_file.stem
                            all_sections.extend(
                                _index_paragraph_groups(spec, text, name),
                            )
                        else:
                            all_sections.extend(
                                _index_markdown_sections(spec, text),
                            )
            continue

        file_path = corpus_path / spec.relative_path
        if not file_path.exists():
            continue

        text = file_path.read_text(errors="replace")
        all_sections.extend(_index_markdown_sections(spec, text))

    return all_sections
