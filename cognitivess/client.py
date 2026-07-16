"""Clientii principali: :class:`Cognitivess` (sync) si :class:`AsyncCognitivess`.

Exemplu::

    from cognitivess import Cognitivess

    cog = Cognitivess(api_key="ssh-ed25519 AAAA...")  # sau COGNITIVESS_API_KEY in env
    resp = cog.chat.completions.create(
        model="Cognitivess-1",
        messages=[{"role": "user", "content": "Salut!"}],
        max_tokens=128,
    )
    print(resp.choices[0].message.content)

    # Stil Anthropic:
    msg = cog.messages.create(
        model="Cognitivess-1",
        max_tokens=128,
        messages=[{"role": "user", "content": "Salut!"}],
    )
    print(msg.content[0].text)
"""

from __future__ import annotations

from ._base_client import SyncAPIClient, AsyncAPIClient, DEFAULT_BASE_URL
from .resources.chat import Chat
from .resources.messages import Messages
from .resources.models import Models
from .resources.responses import Responses


class Cognitivess(SyncAPIClient):
    """Client sincron pentru API-ul CognitivessAI."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        default_headers: dict | None = None,
        env_file: str | None = ".env",
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            env_file=env_file,
        )
        self.chat = Chat(self)
        self.messages = Messages(self)
        self.models = Models(self)
        self.responses = Responses(self)


class AsyncCognitivess(AsyncAPIClient):
    """Client asincron pentru API-ul CognitivessAI."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        default_headers: dict | None = None,
        env_file: str | None = ".env",
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            env_file=env_file,
        )
        self.chat = Chat(self)
        self.messages = Messages(self)
        self.models = Models(self)
        self.responses = Responses(self)