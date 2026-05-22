"""Pure tag-filtering predicates for Section objects."""

from __future__ import annotations

from .indexer import Section


def matches_tags(
    section: Section,
    style: list[str] | None = None,
    type_filter: list[str] | None = None,
    corpus: str | None = None,
) -> bool:
    """Return True if section satisfies all provided tag filters.

    All supplied filters use AND semantics: the section must have ALL
    requested style tags, ALL requested type tags, and match the corpus
    shorthand when supplied. Omitted filters are not applied.
    """
    if corpus is not None and section.shorthand != corpus:
        return False
    if style:
        if not frozenset(style) <= frozenset(section.style_tags):
            return False
    if type_filter:
        if not frozenset(type_filter) <= frozenset(section.type_tags):
            return False
    return True


def filter_sections(
    sections: list[Section],
    style: list[str] | None = None,
    type_filter: list[str] | None = None,
    corpus: str | None = None,
) -> list[Section]:
    """Return sections satisfying all provided tag filters."""
    return [s for s in sections if matches_tags(s, style, type_filter, corpus)]
