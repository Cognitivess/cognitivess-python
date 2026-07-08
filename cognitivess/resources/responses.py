"""Responses — endpoint ``POST /responses`` (OpenAI Responses API).

Foloseste ``input`` (string sau lista de items) si ``max_output_tokens``
(NOT ``max_tokens``).
"""

from __future__ import annotations
from typing import Any


class Responses:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        *,
        model: str,
        input: Any,
        stream: bool = False,
        **kwargs: Any,
    ):
        """Creeaza un raspuns in stilul Responses API.

        ``input``: string simplu sau lista de items (ex: ``[{"role":"user",
        "content":"Hello"}]``). Paseaza ``max_output_tokens``, ``temperature``,
        ``tools``, ``tool_choice``, ``reasoning`` etc. direct.
        """
        body = {"model": model, "input": input, **kwargs}
        if stream:
            body["stream"] = True
            return self._client._stream("POST", "/responses", body)
        return self._client._post("/responses", body)