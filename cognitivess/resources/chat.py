"""Chat completions — endpoint OpenAI-compatible ``POST /chat/completions``."""

from __future__ import annotations
from typing import Any, Iterable


class Completions:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        *,
        model: str,
        messages: Iterable[dict],
        stream: bool = False,
        **kwargs: Any,
    ):
        """Creeaza o completare. Oglinda ``openai.chat.completions.create``.

        Parametrii OpenAI sunt pasati direct: ``temperature``, ``max_tokens``,
        ``top_p``, ``tools``, ``tool_choice``, ``response_format``, ``stop``,
        ``seed``, ``user`` etc.

        Cu ``stream=True`` returneaza un iterator de chunk-uri SSE (sync pe
        :class:`Cognitivess`, async pe :class:`AsyncCognitivess``).
        """
        body = {"model": model, "messages": list(messages), **kwargs}
        if stream:
            body["stream"] = True
            return self._client._stream("POST", "/chat/completions", body)
        return self._client._post("/chat/completions", body)


class Chat:
    def __init__(self, client):
        self.completions = Completions(client)