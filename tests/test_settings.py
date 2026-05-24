"""Tests for the centralized settings module."""
from __future__ import annotations

import pytest


def test_defaults_load() -> None:
    """CorpusSettings loads with sensible defaults."""
    import corpus_inference_query.settings as mod
    mod._settings = None
    s = mod.get_settings()
    assert s.embed_model == "BAAI/bge-base-en-v1.5"
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "olmo3.1:32b"
    assert s.chunk_target_tokens == 512
    mod._settings = None


def test_env_override(monkeypatch) -> None:
    """Env vars with CORPUS_INFERENCE_ prefix override defaults."""
    import corpus_inference_query.settings as mod
    mod._settings = None
    monkeypatch.setenv("CORPUS_INFERENCE_EMBED_MODEL", "test-model")
    monkeypatch.setenv("CORPUS_INFERENCE_OLLAMA_MODEL", "qwen3:32b")
    s = mod.get_settings()
    assert s.embed_model == "test-model"
    assert s.ollama_model == "qwen3:32b"
    mod._settings = None


def test_singleton_caching() -> None:
    """get_settings() returns the same instance on repeated calls."""
    import corpus_inference_query.settings as mod
    mod._settings = None
    s1 = mod.get_settings()
    s2 = mod.get_settings()
    assert s1 is s2
    mod._settings = None
