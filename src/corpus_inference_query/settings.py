"""Centralized configuration via Pydantic BaseSettings."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class CorpusSettings(BaseSettings):
    """Settings for corpus-inference-query, read from env vars."""

    model_config = SettingsConfigDict(env_prefix="CORPUS_INFERENCE_")

    path: Path = Path.home() / "Documents" / "writing-corpus"
    cache_path: Path = Path.home() / ".cache" / "corpus-inference-query" / "lance"
    embed_model: str = "BAAI/bge-base-en-v1.5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "olmo3.1:32b"
    chunk_target_tokens: int = 512
    chunk_max_tokens: int = 1024
    chunk_overlap_tokens: int = 64


_settings: CorpusSettings | None = None


def get_settings() -> CorpusSettings:
    """Return the cached singleton settings instance."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = CorpusSettings()
    return _settings
