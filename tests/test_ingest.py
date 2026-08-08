"""Tests for the ingestion pipeline (chunker, cache, auto-discovery)."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_inference_query.ingest import (
    CHUNK_SIZE,
    chunk_text,
    discover_files,
    discovered_specs,
    file_sections,
    load_ingested_sections,
    run_ingest,
)


@pytest.fixture
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CORPUS_INFERENCE_INGEST_CACHE", str(tmp_path / "cache"))
    root = tmp_path / "corpus"
    (root / "CJ").mkdir(parents=True)
    (root / "CJ" / "dreams.txt").write_text(
        "First paragraph about dreams. " * 80 + "\n\n" + "Second paragraph. " * 80
    )
    (root / "notes.md").write_text("# Notes\n\nShort note on writing style.")
    (root / "CJ" / "cover.jpg").write_bytes(b"\xff\xd8\xff")
    return root


class TestChunkText:
    def test_short_text_single_chunk(self) -> None:
        assert chunk_text("Hello world.") == ["Hello world."]

    def test_empty_text(self) -> None:
        assert chunk_text("") == []
        assert chunk_text("   \n  ") == []

    def test_long_text_splits_with_overlap(self) -> None:
        text = "word " * 1000
        chunks = chunk_text(text)
        assert len(chunks) > 1
        assert all(len(c) <= CHUNK_SIZE for c in chunks)

    def test_prefers_paragraph_boundary(self) -> None:
        para = "a" * 1000
        text = f"{para}\n\n{para}"
        chunks = chunk_text(text)
        assert chunks[0] == para

    def test_normalizes_crlf(self) -> None:
        chunks = chunk_text("line one\r\nline two")
        assert "\r" not in chunks[0]


class TestDiscoverFiles:
    def test_finds_only_text_suffixes(self, corpus: Path) -> None:
        rels = [p.relative_to(corpus) for p in discover_files(corpus)]
        assert Path("CJ/dreams.txt") in rels
        assert Path("notes.md") in rels
        assert all(p.suffix != ".jpg" for p in rels)

    def test_skips_git_dirs(self, corpus: Path) -> None:
        (corpus / ".git").mkdir()
        (corpus / ".git" / "junk.txt").write_text("x")
        rels = [p.relative_to(corpus) for p in discover_files(corpus)]
        assert Path(".git/junk.txt") not in rels


class TestFileSections:
    def test_subdir_becomes_shorthand(self, corpus: Path) -> None:
        rel = Path("CJ/dreams.txt")
        secs = file_sections(rel, (corpus / rel).read_text(), corpus)
        assert secs
        assert secs[0].shorthand == "CJ"
        assert secs[0].citation == "CJ §dreams.1"

    def test_root_file_uses_corpus_dir_name(self, corpus: Path) -> None:
        secs = file_sections(Path("notes.md"), "content long enough here.", corpus)
        assert secs[0].shorthand == corpus.name


class TestRunIngest:
    def test_ingest_and_load_roundtrip(self, corpus: Path) -> None:
        assert run_ingest(corpus, embed=False) == 0
        sections = load_ingested_sections(corpus)
        assert sections
        shorthands = {s.shorthand for s in sections}
        assert "CJ" in shorthands

    def test_skips_unchanged_on_rerun(self, corpus: Path, capsys: pytest.CaptureFixture) -> None:
        run_ingest(corpus, embed=False)
        capsys.readouterr()
        run_ingest(corpus, embed=False)
        out = capsys.readouterr().out
        assert "2 unchanged" in out

    def test_removed_file_pruned_from_cache(self, corpus: Path) -> None:
        run_ingest(corpus, embed=False)
        (corpus / "notes.md").unlink()
        run_ingest(corpus, embed=False)
        shorthands = {s.shorthand for s in load_ingested_sections(corpus)}
        assert shorthands == {"CJ"}

    def test_dry_run_writes_nothing(self, corpus: Path) -> None:
        assert run_ingest(corpus, dry_run=True, embed=False) == 0
        assert load_ingested_sections(corpus) == []

    def test_missing_dir_returns_error(self, tmp_path: Path) -> None:
        assert run_ingest(tmp_path / "nope", embed=False) == 1


class TestDiscoveredSpecs:
    def test_specs_synthesized_after_ingest(self, corpus: Path) -> None:
        run_ingest(corpus, embed=False)
        shorthands = {s.shorthand for s in discovered_specs(corpus)}
        assert "CJ" in shorthands

    def test_empty_before_ingest(self, corpus: Path) -> None:
        assert discovered_specs(corpus) == []


class TestBuildIndexIntegration:
    def test_build_index_prefers_ingest_cache(self, corpus: Path) -> None:
        from corpus_inference_query.indexer import build_index

        run_ingest(corpus, embed=False)
        sections = build_index(corpus)
        assert sections
        assert {s.shorthand for s in sections} == {"CJ", corpus.name}

    def test_repository_search_by_ingested_citation(self, corpus: Path) -> None:
        from corpus_inference_query.corpus_repository import CorpusRepository

        run_ingest(corpus, embed=False)
        repo = CorpusRepository(corpus)
        result = repo.search("CJ §dreams.1", top_k=1)
        assert "CJ §dreams.1" in result
