"""Clienti HTTP de baza (sync + async), fara logica de resurse.

Resursele (chat, messages, models, responses) apeleaza doar ``client._post`` /
``client._get`` / ``client._stream``, care sunt sync pe :class:`SyncAPIClient`
si async pe :class:`AsyncAPIClient`. Astfel codul de resurse e comun.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, Iterator, AsyncIterator, Optional

import httpx

from ._models import _to_attrdict
from .exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from .version import USER_AGENT

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}

_ENV_API_KEY = "COGNITIVESS_API_KEY"


class _BaseClient:
    """Logica comuna sync/async: config, headers, mapare erori."""

    _is_async: bool = False

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        if api_key is None:
            api_key = os.environ.get(_ENV_API_KEY)
        if not api_key:
            raise ValueError(
                "api_key lipseste. Trimite api_key=... sau seteaza "
                f"{_ENV_API_KEY} in env."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._default_headers = default_headers or {}
        self._http = self._make_http()

    # --- construit in subclase ---
    def _make_http(self) -> Any:
        raise NotImplementedError

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return self.base_url + path

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        h.update(self._default_headers)
        if extra:
            h.update(extra)
        return h

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.is_success:
            return
        try:
            body = resp.json()
        except Exception:
            body = None
        message = None
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict):
                message = err.get("message")
            elif isinstance(err, str):
                message = err
            message = message or body.get("message") or body.get("detail")
        if not message:
            try:
                message = resp.text
            except Exception:
                message = resp.reason_phrase
        status = resp.status_code
        if status == 401:
            raise AuthenticationError(message or "Unauthorized", status_code=status, body=body)
        if status == 429:
            raise RateLimitError(message or "Rate limit exceeded", status_code=status, body=body)
        raise APIStatusError(message or f"HTTP {status}", status_code=status, body=body)

    @staticmethod
    def _parse_sse_line(line: str):
        """Returneaza (event_data_dict | None). Sari liniile goale/comment; [DONE] -> None."""
        if not line:
            return None
        if line.startswith(":"):  # keep-alive / comment SSE
            return None
        if line.startswith("data:"):
            data = line[len("data:"):].lstrip()
        elif line.startswith("event:") or line.startswith("id:"):
            return None
        else:
            return None
        data = data.strip()
        if data == "[DONE]":
            return "DONE"
        if not data:
            return None
        return _to_attrdict(json.loads(data))


class SyncAPIClient(_BaseClient):
    """Client HTTP sincron (httpx.Client)."""

    _is_async = False

    def _make_http(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SyncAPIClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        params: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        url = self._url(path)
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.request(
                    method, url, json=body, params=params, headers=self._headers(headers)
                )
            except httpx.TimeoutException as e:
                raise APITimeoutError(str(e) or "Request timed out", cause=e) from e
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise APIConnectionError(str(e) or "Connection error", cause=e) from e
            if resp.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            self._raise_for_status(resp)
            return _to_attrdict(resp.json())
        raise APIConnectionError(str(last_exc) if last_exc else "Request failed")

    def _post(self, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None):
        return self._request("POST", path, body=body, headers=headers)

    def _get(self, path: str, *, params: Any = None, headers: Optional[Dict[str, str]] = None):
        return self._request("GET", path, params=params, headers=headers)

    def _stream(self, method: str, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None):
        """Generator de evenimente SSE. Yield-uieste AttrDict per payload `data:`."""
        url = self._url(path)
        with self._http.stream(method, url, json=body, headers=self._headers(headers)) as resp:
            self._raise_for_status(resp)
            for line in resp.iter_lines():
                parsed = self._parse_sse_line(line)
                if parsed == "DONE":
                    break
                if parsed is not None:
                    yield parsed


class AsyncAPIClient(_BaseClient):
    """Client HTTP asincron (httpx.AsyncClient)."""

    _is_async = True

    def _make_http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncAPIClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        params: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        url = self._url(path)
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._http.request(
                    method, url, json=body, params=params, headers=self._headers(headers)
                )
            except httpx.TimeoutException as e:
                raise APITimeoutError(str(e) or "Request timed out", cause=e) from e
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise APIConnectionError(str(e) or "Connection error", cause=e) from e
            if resp.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            self._raise_for_status(resp)
            return _to_attrdict(resp.json())
        raise APIConnectionError(str(last_exc) if last_exc else "Request failed")

    async def _post(self, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None):
        return await self._request("POST", path, body=body, headers=headers)

    async def _get(self, path: str, *, params: Any = None, headers: Optional[Dict[str, str]] = None):
        return await self._request("GET", path, params=params, headers=headers)

    async def _stream(
        self, method: str, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator:
        """Generator async de evenimente SSE."""
        url = self._url(path)
        async with self._http.stream(method, url, json=body, headers=self._headers(headers)) as resp:
            self._raise_for_status(resp)
            async for line in resp.aiter_lines():
                parsed = self._parse_sse_line(line)
                if parsed == "DONE":
                    break
                if parsed is not None:
                    yield parsed