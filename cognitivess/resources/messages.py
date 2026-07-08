"""Messages — endpoint Anthropic-compatible ``POST /messages``."""

from __future__ import annotations
from typing import Any, Iterable, Optional

# Pe /messages trimitem si x-api-key + anthropic-version pentru compatibilitate
# maxima cu gateway-ul (accepta si Bearer fallback, dar asa e nativ).


class Messages:
    def __init__(self, client):
        self._client = client

    def _headers_for(self) -> dict:
        return {"x-api-key": self._client.api_key, "anthropic-version": "2023-06-01"}

    def create(
        self,
        *,
        model: str,
        messages: Iterable[dict],
        max_tokens: int,
        system: Optional[Any] = None,
        stream: bool = False,
        **kwargs: Any,
    ):
        """Creeaza un mesaj in stil Anthropic. Oglinda ``anthropic.messages.create``.

        ``system`` poate fi string sau lista de content blocks. ``tools``,
        ``tool_choice``, ``temperature``, ``top_p``, ``stop_sequences``, ``metadata``
        etc. sunt pasate direct.
        """
        body: dict = {"model": model, "messages": list(messages), "max_tokens": max_tokens, **kwargs}
        if system is not None:
            body["system"] = system
        headers = self._headers_for()
        if stream:
            body["stream"] = True
            return self._client._stream("POST", "/messages", body, headers=headers)
        return self._client._post("/messages", body, headers=headers)