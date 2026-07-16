"""Clienti HTTP de baza (sync + async), fara logica de resurse.

Resursele (chat, messages, models, responses) apeleaza doar ``client._post`` /
``client._get`` / ``client._stream``, care sunt sync pe :class:`SyncAPIClient`
si async pe :class:`AsyncAPIClient`. Astfel codul de resurse e comun.
"""

from __future__ import annotations

import asyncio
import email.utils
import json
import os
import random
import time
from typing import Any, AsyncIterator, Dict, Optional

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

DEFAULT_BASE_URL = "https://api.cognitivess.com/v1"

_ENV_API_KEY = "COGNITIVESS_API_KEY"
_ENV_BASE_URL = "COGNITIVESS_BASE_URL"


def _load_env_file(path: str) -> None:
    """Parser .env minimal, fara dependinta de python-dotenv.

    Citeste ``path`` (de ex ``.env`` din cwd) si seteaza in ``os.environ`` DOAR
    cheile care nu sunt deja definite. Suporta: ``KEY=VALUE``, comentarii ``#``,
    prefix ``export``, ghilimele simple/duble. Nu suprascrie env-ul existent si
    nu ridica niciodata exceptie — daca fisierul lipseste sau e invalid, e no-op.
    """
    if not path or not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].lstrip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if not key or key in os.environ:
                    continue
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                os.environ[key] = value
    except Exception:
        return


def _json_or_text(resp: httpx.Response):
    """Parseaza corpul unui response de succes. JSON -> dict/list, altfel
    string-ul raw, altfel None (ex: 204 No Content). Nu ridica niciodata
    JSONDecodeError in afara ierarhiei CognitivessError."""
    if resp.status_code == 204 or not resp.content:
        return None
    try:
        return resp.json()
    except Exception:
        try:
            return resp.text
        except Exception:
            return None


class _BaseClient:
    """Logica comuna sync/async: config, headers, mapare erori."""

    _is_async: bool = False

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Dict[str, str]] = None,
        env_file: Optional[str] = ".env",
    ):
        # .env se incarca devreme, ca si COGNITIVESS_BASE_URL sa poata fi
        # rezolvat din fisier. Nu suprascrie env-ul deja definit.
        if env_file:
            _load_env_file(env_file)
        if api_key is None:
            api_key = os.environ.get(_ENV_API_KEY)
        if not api_key:
            raise ValueError(
                "api_key lipseste. Trimite api_key=... sau seteaza "
                f"{_ENV_API_KEY} in env."
            )
        self.api_key = api_key
        if not base_url:
            base_url = os.environ.get(_ENV_BASE_URL) or DEFAULT_BASE_URL
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
    def _retry_delay(resp: Optional[httpx.Response], attempt: int) -> float:
        """Backoff pentru retry. Honoreaza ``Retry-After`` (secunde sau HTTP-date),
        altfel exponential cu jitter. ``attempt`` e 0-indexat."""
        if resp is not None:
            retry_after = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
                try:  # HTTP-date format
                    parsed = email.utils.parsedate_to_datetime(retry_after)
                    delta = parsed.timestamp() - time.time()
                    if delta > 0:
                        return delta
                except Exception:
                    pass
        # exponential cu jitter full, capat la ~8s
        base = min(0.5 * (2 ** attempt), 8.0)
        return base + random.uniform(0, 0.25)

    @staticmethod
    def _extract_message(resp: httpx.Response):
        """Extrage mesajul de eroare dintr-un response deja citit. Pentru
        streaming, apelantul trebuie sa fi facut ``read()``/``aread()`` inainte."""
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
        return message, body

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.is_success:
            return
        message, body = _BaseClient._extract_message(resp)
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
        # connect scurt, read = self.timeout. read-ul mare tine si in streaming
        # (model de reasoning cu pauze lungi intre evenimentele SSE).
        return httpx.Client(timeout=httpx.Timeout(self.timeout, connect=10.0))

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
        timeout: Optional[float] = None,
    ):
        url = self._url(path)
        last_exc: Optional[Exception] = None
        req_timeout = timeout if timeout is not None else self.timeout
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.request(
                    method, url, json=body, params=params,
                    headers=self._headers(headers), timeout=req_timeout,
                )
            except httpx.TimeoutException as e:
                raise APITimeoutError(str(e) or "Request timed out", cause=e) from e
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self.max_retries:
                    time.sleep(self._retry_delay(None, attempt))
                    continue
                raise APIConnectionError(str(e) or "Connection error", cause=e) from e
            if resp.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                time.sleep(self._retry_delay(resp, attempt))
                continue
            self._raise_for_status(resp)
            return _to_attrdict(_json_or_text(resp))
        raise APIConnectionError(str(last_exc) if last_exc else "Request failed")

    def _post(self, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None):
        return self._request("POST", path, body=body, headers=headers, timeout=timeout)

    def _get(self, path: str, *, params: Any = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None):
        return self._request("GET", path, params=params, headers=headers, timeout=timeout)

    def _stream(self, method: str, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None):
        """Generator de evenimente SSE. Yield-uieste AttrDict per payload `data:`."""
        url = self._url(path)
        req_timeout = timeout if timeout is not None else self.timeout
        with self._http.stream(method, url, json=body, headers=self._headers(headers), timeout=req_timeout) as resp:
            if not resp.is_success:
                resp.read()  # corpul trebuie citit inainte de .json()/.text()
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
        return httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0))

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
        timeout: Optional[float] = None,
    ):
        url = self._url(path)
        last_exc: Optional[Exception] = None
        req_timeout = timeout if timeout is not None else self.timeout
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._http.request(
                    method, url, json=body, params=params,
                    headers=self._headers(headers), timeout=req_timeout,
                )
            except httpx.TimeoutException as e:
                raise APITimeoutError(str(e) or "Request timed out", cause=e) from e
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(None, attempt))
                    continue
                raise APIConnectionError(str(e) or "Connection error", cause=e) from e
            if resp.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                await asyncio.sleep(self._retry_delay(resp, attempt))
                continue
            self._raise_for_status(resp)
            return _to_attrdict(_json_or_text(resp))
        raise APIConnectionError(str(last_exc) if last_exc else "Request failed")

    async def _post(self, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None):
        return await self._request("POST", path, body=body, headers=headers, timeout=timeout)

    async def _get(self, path: str, *, params: Any = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None):
        return await self._request("GET", path, params=params, headers=headers, timeout=timeout)

    async def _stream(
        self, method: str, path: str, body: Any, *, headers: Optional[Dict[str, str]] = None, timeout: Optional[float] = None
    ) -> AsyncIterator:
        """Generator async de evenimente SSE."""
        url = self._url(path)
        req_timeout = timeout if timeout is not None else self.timeout
        async with self._http.stream(method, url, json=body, headers=self._headers(headers), timeout=req_timeout) as resp:
            if not resp.is_success:
                await resp.aread()  # corpul trebuie citit inainte de .json()/.text()
                self._raise_for_status(resp)
            async for line in resp.aiter_lines():
                parsed = self._parse_sse_line(line)
                if parsed == "DONE":
                    break
                if parsed is not None:
                    yield parsed