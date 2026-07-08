"""CognitivessAI Python SDK.

SDK OpenAI- si Anthropic-compatible pentru API-ul CognitivessAI (modelul Cognitivess-1).

Instalare::

    pip install cognitivess

Folosire::

    from cognitivess import Cognitivess
    cog = Cognitivess()  # citeste COGNITIVESS_API_KEY din env
    print(cog.chat.completions.create(
        model="Cognitivess-1",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=128,
    ).choices[0].message.content)
"""

from .client import Cognitivess, AsyncCognitivess, DEFAULT_BASE_URL
from .exceptions import (
    CognitivessError,
    APIError,
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from .version import __version__

__all__ = [
    "Cognitivess",
    "AsyncCognitivess",
    "DEFAULT_BASE_URL",
    "CognitivessError",
    "APIError",
    "APIStatusError",
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "RateLimitError",
    "__version__",
]