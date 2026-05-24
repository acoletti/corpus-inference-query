"""Ollama SDK facade (OpenAI-compatible). Optional — requires ``openai``."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pydantic import BaseModel
_FACADE_UNAVAILABLE, _facade = object(), None

class OllamaFacade:
    """Thin wrapper around the OpenAI-compatible Ollama endpoint."""
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url, self._model, self._client = base_url, model, None

    def complete(self, system: str, user: str, response_model: type[BaseModel] | None = None) -> str | None:
        if self._client is None:
            from openai import OpenAI  # noqa: PLC0415
            self._client = OpenAI(base_url=f"{self._base_url}/v1", api_key="ollama")
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        fmt = {"response_format": {"type": "json_object"}} if response_model else {}
        try:
            text = self._client.chat.completions.create(
                model=self._model, messages=msgs, **fmt).choices[0].message.content
        except Exception:
            return None
        if response_model is not None:
            response_model.model_validate_json(text)
        return text

def get_facade() -> OllamaFacade | None:
    """Return the module-level singleton, or *None* if unavailable."""
    global _facade  # noqa: PLW0603
    if _facade is _FACADE_UNAVAILABLE:
        return None
    if _facade is None:
        try:
            from .settings import get_settings as _gs  # noqa: PLC0415
            _facade = OllamaFacade(_gs().ollama_base_url, _gs().ollama_model)
        except Exception:
            _facade = _FACADE_UNAVAILABLE
            return None
    return _facade
