"""Models — ``GET /models`` (listeaza modelele disponibile)."""

from __future__ import annotations
from typing import Optional


class Models:
    def __init__(self, client):
        self._client = client

    def list(self):
        """Listeaza modelele disponibile (ex: Cognitivess-1)."""
        return self._client._get("/models")

    def retrieve(self, model_id: str, *, timeout: Optional[float] = None):
        """Detaliile unui model individual — ``GET /models/{model_id}``."""
        return self._client._get(f"/models/{model_id}", timeout=timeout)