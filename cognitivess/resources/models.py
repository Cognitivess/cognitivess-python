"""Models — ``GET /models`` (listeaza modelele disponibile)."""

from __future__ import annotations


class Models:
    def __init__(self, client):
        self._client = client

    def list(self):
        """Listeaza modelele disponibile (ex: Cognitivess-1)."""
        return self._client._get("/models")