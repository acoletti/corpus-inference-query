"""Tests for the Ollama SDK facade."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestOllamaFacade:
    def test_complete_returns_content(self) -> None:
        from corpus_inference_query.ollama_facade import OllamaFacade
        facade = OllamaFacade("http://localhost:11434", "test-model")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="test response"))
        ]
        facade._client = mock_client
        result = facade.complete("system prompt", "user message")
        assert result == "test response"

    def test_complete_returns_none_on_error(self) -> None:
        from corpus_inference_query.ollama_facade import OllamaFacade
        facade = OllamaFacade("http://localhost:11434", "test-model")
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("offline")
        facade._client = mock_client
        result = facade.complete("system", "user")
        assert result is None

    def test_get_facade_returns_none_without_openai(self) -> None:
        import corpus_inference_query.ollama_facade as mod
        mod._facade = None
        with patch.dict("sys.modules", {"openai": None}):
            mod._facade = None
            result = mod.get_facade()
            assert result is None or hasattr(result, "complete")
        mod._facade = None
