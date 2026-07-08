"""Resurse SDK: chat, messages, models, responses.

Fiecare resursa e agnostica sync/async: apeleaza ``self._client._post`` /
``self._client._stream``. Pe clientul sync acestea returneaza direct rezultatul
sau un iterator; pe cel async returneaza o coroutine, respectiv un async iterator.
Astfel codul de resurse e scris o singura data.
"""

from .chat import Chat, Completions
from .messages import Messages
from .models import Models
from .responses import Responses

__all__ = ["Chat", "Completions", "Messages", "Models", "Responses"]