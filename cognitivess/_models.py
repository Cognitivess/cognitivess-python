"""Modele usoare de raspuns.

Evitam Pydantic pentru a tine SDK-ul fara dependente grele. Raspunsurile JSON
sunt transformate recursiv in :class:`AttrDict`, care permite acces prin atribut
la fel ca obiectele din SDK-ul OpenAI::

    resp.choices[0].message.content
"""

from __future__ import annotations
from typing import Any


class AttrDict(dict):
    """dict cu acces prin atribut. Nested dict/list sunt convertite de _to_attrdict."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


def _to_attrdict(obj: Any) -> Any:
    """Conversie recursiva dict->AttrDict, prin liste si alte containere."""
    if isinstance(obj, dict):
        return AttrDict({k: _to_attrdict(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_attrdict(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_to_attrdict(v) for v in obj)
    return obj