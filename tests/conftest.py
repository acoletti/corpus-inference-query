"""Shared test fixtures: isolate on-disk caches from the user's real ones."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_caches(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point ingest + embedding caches at per-test temp dirs.

    Without this, tests that call run_ingest()/_run_init() would write into
    (and read stale sections from) ~/.cache/corpus-inference-query.
    """
    monkeypatch.setenv("CORPUS_INFERENCE_INGEST_CACHE", str(tmp_path / "ingest-cache"))
    monkeypatch.setenv("CORPUS_INFERENCE_CACHE_PATH", str(tmp_path / "lance-cache"))
