"""Chat completions — endpoint OpenAI-compatible ``POST /chat/completions``."""

from __future__ import annotations
from typing import Any, Iterable, Iterator, AsyncIterator, Optional


class Completions:
    def __init__(self, client):
        self._client = client

    def create(
        self,
        *,
        model: str,
        messages: Iterable[dict],
        stream: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ):
        """Creeaza o completare. Oglinda ``openai.chat.completions.create``.

        Parametrii OpenAI sunt pasati direct: ``temperature``, ``max_tokens``,
        ``top_p``, ``tools``, ``tool_choice``, ``response_format``, ``stop``,
        ``seed``, ``user`` etc.

        ``timeout`` (optional, secunde) suprascrie timeout-ul clientului doar
        pentru aceasta cerere — nu e trimis in corpul JSON.

        Cu ``stream=True`` returneaza un iterator de chunk-uri SSE (sync pe
        :class:`Cognitivess`, async pe :class:`AsyncCognitivess``).
        """
        body = {"model": model, "messages": list(messages), **kwargs}
        if stream:
            body["stream"] = True
            return self._client._stream("POST", "/chat/completions", body, timeout=timeout)
        return self._client._post("/chat/completions", body, timeout=timeout)

    def iter_text(self, *, model: str, messages: Iterable[dict], timeout: Optional[float] = None, **kwargs: Any):
        """Convenienta de streaming: yield-uieste DOAR string-urile de continut
        (delta.content), sarind chunk-urile de metadata / choices goale.

        Sync pe :class:`Cognitivess` (``for text in ...``), async pe
        :class:`AsyncCognitivess` (``async for text in ...``). Echivalent cu::

            for chunk in cog.chat.completions.create(..., stream=True):
                if chunk.choices:
                    c = getattr(chunk.choices[0].delta, "content", None)
                    if c:
                        yield c
        """
        if self._client._is_async:
            return self._iter_text_async(model, messages, timeout=timeout, **kwargs)
        return self._iter_text_sync(model, messages, timeout=timeout, **kwargs)

    def _iter_text_sync(self, model, messages, *, timeout=None, **kwargs) -> Iterator[str]:
        for chunk in self.create(model=model, messages=messages, stream=True, timeout=timeout, **kwargs):
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if content:
                yield content

    async def _iter_text_async(self, model, messages, *, timeout=None, **kwargs) -> AsyncIterator[str]:
        async for chunk in self.create(model=model, messages=messages, stream=True, timeout=timeout, **kwargs):
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if content:
                yield content


class Chat:
    def __init__(self, client):
        self.completions = Completions(client)