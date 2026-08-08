"""Repository façade: corpus loading, section access, and result types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .corpus_config import load_corpus_specs
from .detectors import StandardsCheckResult, run_checks
from .indexer import Section, build_index
from .search import (
    _format_results,
    _parse_citation,
    _score_section,
    _tokenize_query,
)
from .search import (
    search as _search_corpus,
)
from .tag_filter import filter_sections
from .text_utils import split_sentences
from .vector_store import best_similarity, build_vector_store, vector_search

# Sentinel distinguishing "not yet tried" (None) from "unavailable" after failure.
_VECTOR_STORE_UNAVAILABLE = object()


@dataclass
class CorpusSummary:
    shorthand: str
    title: str
    author: str
    default_style: list[str]
    default_type: list[str]
    doc_count: int


@dataclass
class ScoredSection:
    section: Section
    score: float


@dataclass
class ReloadResult:
    status: str
    corpora_count: int
    doc_count: int


class CorpusRepository:
    """Owns all corpus state: lazy-loaded index, vector store, and specs."""

    def __init__(self, corpus_path: Path) -> None:
        self._corpus_path = corpus_path
        self._index: list[Section] | None = None
        self._vector_store: object = None  # None | _VECTOR_STORE_UNAVAILABLE | lancedb.Table

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_index(self) -> list[Section]:
        if self._index is None:
            if not self._corpus_path.exists():
                raise RuntimeError(
                    f"Corpus path does not exist: {self._corpus_path}\n"
                    f"Set CORPUS_INFERENCE_PATH to the correct location."
                )
            raw = build_index(self._corpus_path)
            self._index = self._enrich_with_spec_tags(raw)
        return self._index

    def _enrich_with_spec_tags(self, sections: list[Section]) -> list[Section]:
        """Propagate corpus-level style/type tags to sections that have none.

        build_index() creates Section objects without copying style_tags /
        type_tags from CorpusSpec. This method back-fills those fields so
        tag-based filtering works against real (non-mocked) fixture corpora.
        Only sections whose own tags are empty are updated; sections with
        explicit per-section tags are left untouched.
        """
        corpus_toml = self._corpus_path / "corpus.toml"
        specs = load_corpus_specs(corpus_toml)
        spec_map: dict[str, tuple[list[str], list[str]]] = {
            s.shorthand: (s.style_tags, s.type_tags) for s in specs
        }
        result: list[Section] = []
        for sec in sections:
            if (not sec.style_tags or not sec.type_tags) and sec.shorthand in spec_map:
                spec_style, spec_type = spec_map[sec.shorthand]
                result.append(Section(
                    corpus_id=sec.corpus_id,
                    shorthand=sec.shorthand,
                    chapter=sec.chapter,
                    section_name=sec.section_name,
                    citation=sec.citation,
                    content=sec.content,
                    line_start=sec.line_start,
                    keywords=sec.keywords,
                    style_tags=sec.style_tags if sec.style_tags else list(spec_style),
                    type_tags=sec.type_tags if sec.type_tags else list(spec_type),
                ))
            else:
                result.append(sec)
        return result

    def _get_vector_store(self) -> object:
        if self._vector_store is None:
            try:
                self._vector_store = build_vector_store(self._get_index())
            except Exception:
                self._vector_store = _VECTOR_STORE_UNAVAILABLE
        if self._vector_store is _VECTOR_STORE_UNAVAILABLE:
            return None
        return self._vector_store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_corpora(self) -> list[CorpusSummary]:
        """Return one summary per corpus, with section counts."""
        index = self._get_index()
        corpus_toml = self._corpus_path / "corpus.toml"
        specs = load_corpus_specs(corpus_toml)

        counts: dict[str, int] = {}
        for s in index:
            counts[s.shorthand] = counts.get(s.shorthand, 0) + 1

        return [
            CorpusSummary(
                shorthand=spec.shorthand,
                title=spec.title,
                author=spec.author,
                default_style=spec.style_tags,
                default_type=spec.type_tags,
                doc_count=counts.get(spec.shorthand, 0),
            )
            for spec in specs
        ]

    def search(
        self,
        query: str,
        top_k: int = 8,
        style: list[str] | None = None,
        type_filter: list[str] | None = None,
        corpus: str | None = None,
        max_chars: int = 6000,
    ) -> str:
        """NL or citation search with optional tag/corpus filters."""
        index = filter_sections(self._get_index(), style, type_filter, corpus)
        if not index:
            return "No sections match the provided filters."
        # Try vector search first for NL queries (no § sigil)
        shorthand, _ = _parse_citation(query)
        if not shorthand:
            table = self._get_vector_store()
            if table is not None:
                try:
                    nl_sections = vector_search(table, self._get_index(), query, top_k)
                    if nl_sections:
                        filtered = [s for s in nl_sections if s in index]
                        if filtered:
                            return _format_results(filtered[:top_k], max_chars)
                except Exception:
                    pass
        return _search_corpus(index, query, top_k=top_k, max_chars=max_chars)

    def lookup_citation(self, citation: str, max_chars: int = 6000) -> str:
        """Resolve a shorthand citation to its section text."""
        return _search_corpus(self._get_index(), citation, max_chars=max_chars)

    def find_exemplars(
        self,
        style: list[str] | None = None,
        type_filter: list[str] | None = None,
        length: str | None = None,
        register: str | None = None,
        top_k: int = 5,
        max_chars: int = 6000,
    ) -> str:
        """Filter sections by tags and optional length bucket."""
        sections = filter_sections(self._get_index(), style, type_filter)
        if length:
            sections = _filter_by_length(sections, length)
        if not sections:
            return "No exemplars found matching the provided criteria."
        return _format_results(sections[:top_k], max_chars)

    def find_similar_voice(
        self,
        text: str,
        top_k: int = 5,
        corpus: str = "personal",
        max_chars: int = 6000,
    ) -> str:
        """Vector similarity search against a named corpus. Returns empty result gracefully."""
        pool = filter_sections(self._get_index(), corpus=corpus)
        if not pool:
            return f"No sections found for corpus '{corpus}'. Add personal writings to use this tool."
        table = self._get_vector_store()
        if table is not None:
            try:
                results = vector_search(table, pool, text, top_k)
                if results:
                    return _format_results(results, max_chars)
            except Exception:
                pass
        # Keyword fallback
        tokens = _tokenize_query(text)
        scored = sorted(((s, _score_section(s, tokens)) for s in pool), key=lambda x: x[1], reverse=True)
        top = [s for s, sc in scored[:top_k] if sc > 0]
        if not top:
            return f"No similar sections found in corpus '{corpus}'."
        return _format_results(top, max_chars)

    def suggest_opening(
        self,
        type_name: str,
        style: list[str] | None = None,
        topic: str | None = None,
        top_k: int = 5,
        max_chars: int = 6000,
    ) -> str:
        """Return first sentences from sections matching type/style."""
        sections = filter_sections(self._get_index(), style=style, type_filter=[type_name])
        if topic:
            tokens = _tokenize_query(topic)
            sections = sorted(sections, key=lambda s: _score_section(s, tokens), reverse=True)
        candidates = sections[:top_k * 3]  # over-fetch for first-sentence extraction
        openings = []
        for s in candidates:
            sentences = split_sentences(s.content)
            first = sentences[0] if sentences else ""
            if first and len(first) > 10:
                openings.append(Section(
                    corpus_id=s.corpus_id,
                    shorthand=s.shorthand,
                    chapter=s.chapter,
                    section_name=s.section_name,
                    citation=s.citation,
                    content=first,
                    line_start=s.line_start,
                    style_tags=s.style_tags,
                    type_tags=s.type_tags,
                ))
            if len(openings) >= top_k:
                break
        if not openings:
            return f"No opening sentences found for type='{type_name}'."
        return _format_results(openings, max_chars)

    def suggest_rewrite(
        self,
        text: str,
        target_style: str,
        top_k: int = 5,
        max_chars: int = 6000,
    ) -> str:
        """Return exemplar passages in target_style, ranked by similar length."""
        pool = filter_sections(self._get_index(), style=[target_style])
        if not pool:
            return f"No sections found with style tag '{target_style}'."
        text_len = len(text)
        ranked = sorted(pool, key=lambda s: abs(len(s.content) - text_len))
        return _format_results(ranked[:top_k], max_chars)

    def reload(self) -> ReloadResult:
        """Re-index from disk."""
        self._index = None
        self._vector_store = None
        index = self._get_index()
        corpus_toml = self._corpus_path / "corpus.toml"
        specs = load_corpus_specs(corpus_toml)
        return ReloadResult(
            status="ok",
            corpora_count=len(specs),
            doc_count=len(index),
        )

    def check_against_standards(
        self, text: str, types: list[str] | None = None
    ) -> StandardsCheckResult:
        """Run mechanical writing-standards detectors against text."""
        return run_checks(text, types, self)

    def has_corpus_sections(self, corpus: str) -> bool:
        """True if any indexed section matches the given corpus shorthand."""
        return bool(filter_sections(self._get_index(), corpus=corpus))

    def voice_similarity_score(self, text: str, corpus: str = "personal") -> float | None:
        """Best approximate cosine similarity of text to corpus's vector index.

        Returns None if the corpus is empty or the vector backend is unavailable.
        """
        pool = filter_sections(self._get_index(), corpus=corpus)
        if not pool:
            return None
        table = self._get_vector_store()
        if table is None:
            return None
        try:
            return best_similarity(table, text)
        except Exception:
            return None

    def find_exemplar_section(
        self,
        style: list[str] | None = None,
        type_filter: list[str] | None = None,
        corpus: str | None = None,
    ) -> Section | None:
        """Raw single-section lookup for detector exemplar resolution."""
        sections = filter_sections(self._get_index(), style, type_filter, corpus)
        return sections[0] if sections else None


def _filter_by_length(sections: list[Section], length: str) -> list[Section]:
    """Filter sections by length bucket: 'short' (<500), 'medium' (500-2000), 'long' (>2000)."""
    if length == "short":
        return [s for s in sections if len(s.content) < 500]
    if length == "medium":
        return [s for s in sections if 500 <= len(s.content) < 2000]
    if length == "long":
        return [s for s in sections if len(s.content) >= 2000]
    return sections
