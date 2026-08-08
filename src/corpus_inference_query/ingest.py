"""Ingestion pipeline: walk an unformatted corpus directory, chunk text files,
cache sections, and warm the vector index.

Modeled on the sec-skills/sendme ingestion pattern: recursive walk,
boundary-aware chunking (1500/200), sha256 skip-unchanged, idempotent re-runs.
Output is a per-corpus-path cache (manifest.json + sections.jsonl) that
build_index() merges into the live section index.

Usage:
  corpus-inference-query ingest /path/to/corpus [--dry-run] [--no-skip]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .corpus_config import CorpusSpec
from .indexer import Section, _extract_keywords

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
SUFFIXES = {".md", ".markdown", ".rst", ".txt"}
_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}

_DEFAULT_INGEST_CACHE = Path.home() / ".cache" / "corpus-inference-query" / "ingest"


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Boundary-aware splitter: prefer paragraph, then sentence, then line."""
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = start + size
        if end < len(cleaned):
            for probe, skip in (("\n\n", 2), (". ", 2), ("\n", 1)):
                cut = cleaned.rfind(probe, start + size // 2, end)
                if cut != -1:
                    end = cut + skip
                    break
        if chunk := cleaned[start:end].strip():
            chunks.append(chunk)
        start = end - overlap
        if start >= len(cleaned):
            break
    return chunks


def _slug(name: str) -> str:
    return re.sub(r"\s+", "-", name.strip())


def _ingest_cache_root() -> Path:
    return Path(os.environ.get("CORPUS_INFERENCE_INGEST_CACHE", str(_DEFAULT_INGEST_CACHE)))


def cache_dir_for(corpus_path: Path) -> Path:
    digest = hashlib.sha256(str(corpus_path.resolve()).encode()).hexdigest()[:12]
    return _ingest_cache_root() / digest


def discover_files(corpus_path: Path) -> list[Path]:
    """All ingestable text files under corpus_path, sorted for determinism."""
    return sorted(
        p for p in corpus_path.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUFFIXES
        and not _SKIP_DIRS.intersection(p.parts)
        and p.name != "corpus.toml"
    )


def _shorthand_for(rel: Path, corpus_path: Path) -> str:
    """Corpus shorthand: top-level subdirectory name, or the root dir name."""
    if len(rel.parts) > 1:
        return _slug(rel.parts[0])
    return _slug(corpus_path.name)


def file_sections(rel: Path, text: str, corpus_path: Path) -> list[Section]:
    """Chunk one file into citable Sections: `<shorthand> §<stem>.<n>`."""
    shorthand = _shorthand_for(rel, corpus_path)
    chapter = rel.stem
    sections = []
    for i, chunk in enumerate(chunk_text(text), start=1):
        name = f"{chapter}.{i}"
        sections.append(Section(
            corpus_id=shorthand.lower(),
            shorthand=shorthand,
            chapter=chapter,
            section_name=name,
            citation=f"{shorthand} §{name}",
            content=chunk,
            line_start=i,
            keywords=_extract_keywords(chunk) | _extract_keywords(chapter),
        ))
    return sections


def _section_to_dict(s: Section) -> dict:
    return {
        "corpus_id": s.corpus_id,
        "shorthand": s.shorthand,
        "chapter": s.chapter,
        "section_name": s.section_name,
        "citation": s.citation,
        "content": s.content,
        "line_start": s.line_start,
        "keywords": sorted(s.keywords),
        "style_tags": s.style_tags,
        "type_tags": s.type_tags,
    }


def _section_from_dict(d: dict) -> Section:
    return Section(
        corpus_id=d["corpus_id"],
        shorthand=d["shorthand"],
        chapter=d["chapter"],
        section_name=d["section_name"],
        citation=d["citation"],
        content=d["content"],
        line_start=d["line_start"],
        keywords=set(d.get("keywords", [])),
        style_tags=list(d.get("style_tags", [])),
        type_tags=list(d.get("type_tags", [])),
    )


@dataclass
class Manifest:
    corpus_path: str
    files: dict[str, dict] = field(default_factory=dict)  # rel -> {hash, chunks}
    updated_at: float = 0.0


def _load_manifest(cache_dir: Path) -> Manifest | None:
    path = cache_dir / "manifest.json"
    try:
        data = json.loads(path.read_text())
        return Manifest(
            corpus_path=data["corpus_path"],
            files=data.get("files", {}),
            updated_at=data.get("updated_at", 0.0),
        )
    except (OSError, ValueError, KeyError):
        return None


def _save_manifest(cache_dir: Path, manifest: Manifest) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "manifest.json").write_text(json.dumps({
        "corpus_path": manifest.corpus_path,
        "files": manifest.files,
        "updated_at": manifest.updated_at,
    }, indent=2) + "\n")


def _sections_file(cache_dir: Path, rel: Path) -> Path:
    safe = hashlib.sha256(str(rel).encode()).hexdigest()[:16]
    return cache_dir / "sections" / f"{safe}.jsonl"


def _write_sections(cache_dir: Path, rel: Path, sections: list[Section]) -> None:
    out = _sections_file(cache_dir, rel)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for s in sections:
            f.write(json.dumps(_section_to_dict(s)) + "\n")


def load_ingested_sections(corpus_path: Path) -> list[Section]:
    """Load cached sections for corpus_path; [] when never ingested."""
    cache_dir = cache_dir_for(corpus_path)
    manifest = _load_manifest(cache_dir)
    if manifest is None:
        return []
    sections: list[Section] = []
    for rel in sorted(manifest.files):
        path = _sections_file(cache_dir, Path(rel))
        if not path.exists():
            continue
        with path.open() as f:
            sections.extend(_section_from_dict(json.loads(line)) for line in f if line.strip())
    return sections


def ingested_shorthands(corpus_path: Path) -> list[str]:
    """Distinct corpus shorthands present in the ingest cache, sorted."""
    manifest = _load_manifest(cache_dir_for(corpus_path))
    if manifest is None:
        return []
    return sorted({
        _shorthand_for(Path(rel), corpus_path) for rel in manifest.files
    })


def discovered_specs(corpus_path: Path) -> list[CorpusSpec]:
    """Synthesize one CorpusSpec per ingested shorthand for list_corpora()."""
    return [
        CorpusSpec(
            corpus_id=sh.lower(),
            shorthand=sh,
            relative_path=sh,
            section_pattern=re.compile(r"^# (.+)$"),
            description=f"Auto-discovered corpus '{sh}' (ingested)",
            is_directory=True,
            title=sh,
        )
        for sh in ingested_shorthands(corpus_path)
    ]


def run_ingest(
    corpus_path: Path,
    dry_run: bool = False,
    no_skip: bool = False,
    embed: bool = True,
) -> int:
    """Walk, chunk, cache, and (optionally) warm the vector index. Returns exit code."""
    corpus_path = corpus_path.expanduser().resolve()
    if not corpus_path.is_dir():
        print(f"[ingest] corpus dir not found: {corpus_path}", file=sys.stderr)
        return 1

    files = discover_files(corpus_path)
    if not files:
        print(f"[ingest] no ingestable files (*.txt, *.md, *.rst) under {corpus_path}", file=sys.stderr)
        return 1

    cache_dir = cache_dir_for(corpus_path)
    manifest = (None if no_skip else _load_manifest(cache_dir)) or Manifest(str(corpus_path))
    manifest.corpus_path = str(corpus_path)

    total_chunks = skipped = 0
    seen: set[str] = set()
    for path in files:
        rel = path.relative_to(corpus_path)
        seen.add(str(rel))
        text = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(text.encode()).hexdigest()
        prior = manifest.files.get(str(rel))
        if prior and prior.get("hash") == digest and not dry_run:
            skipped += 1
            continue
        sections = file_sections(rel, text, corpus_path)
        if not dry_run:
            _write_sections(cache_dir, rel, sections)
            manifest.files[str(rel)] = {"hash": digest, "chunks": len(sections)}
        total_chunks += len(sections)
        print(f"[ingest] {rel}: {len(sections)} chunk(s)")

    # Drop stale entries for deleted files.
    for rel in [r for r in manifest.files if r not in seen]:
        _sections_file(cache_dir, Path(rel)).unlink(missing_ok=True)
        del manifest.files[rel]

    if not dry_run:
        manifest.updated_at = time.time()
        _save_manifest(cache_dir, manifest)

    print(
        f"[ingest] done: {len(files) - skipped} file(s) processed, "
        f"{skipped} unchanged, {total_chunks} chunk(s)"
        + (" [dry-run]" if dry_run else "")
    )

    if not dry_run and embed:
        _warm_vector_index(corpus_path)
    return 0


def _warm_vector_index(corpus_path: Path) -> None:
    """Build the LanceDB embedding cache now instead of on first NL query."""
    try:
        from .indexer import build_index
        from .vector_store import build_vector_store
    except ImportError:
        return
    try:
        print("[ingest] building vector index (first run downloads the embed model)...")
        build_vector_store(build_index(corpus_path))
        print("[ingest] vector index ready")
    except ImportError:
        print("[ingest] vector extras not installed — skipping embeddings "
              "(install with: uv sync --extra vector)")
    except Exception as exc:
        print(f"[ingest] vector index build failed (non-fatal): {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="corpus-inference-query ingest",
        description="Ingest an unformatted directory of text files into the corpus cache",
    )
    parser.add_argument("corpus_path", type=Path, help="Directory containing .txt/.md files")
    parser.add_argument("--dry-run", action="store_true", help="chunk only; no cache/embed")
    parser.add_argument("--no-skip", action="store_true", help="re-ingest unchanged files")
    parser.add_argument("--no-embed", action="store_true", help="skip vector index warmup")
    args = parser.parse_args(argv)
    return run_ingest(
        args.corpus_path,
        dry_run=args.dry_run,
        no_skip=args.no_skip,
        embed=not args.no_embed,
    )


if __name__ == "__main__":
    sys.exit(main())
