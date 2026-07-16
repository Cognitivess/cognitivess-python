"""Smoke tests care nu lovesc rețeaua.

Verifica constructia clientilor, ergonomia obiectelor, parsarea SSE si ca
resursele cheama caile/corecte fara HTTP real (monkeypatch pe httpx).
"""

import json

import pytest

import cognitivess
from cognitivess import Cognitivess, AsyncCognitivess
from cognitivess._models import _to_attrdict
from cognitivess._base_client import _BaseClient


def test_version_exported():
    assert isinstance(cognitivess.__version__, str) and cognitivess.__version__


def test_requires_api_key():
    import os
    saved = os.environ.pop("COGNITIVESS_API_KEY", None)
    try:
        with pytest.raises(ValueError):
            Cognitivess(env_file=None)  # explicit: no .env fallback
    finally:
        if saved is not None:
            os.environ["COGNITIVESS_API_KEY"] = saved


def test_env_file_loaded_as_fallback(tmp_path):
    """Fara load_dotenv(), SDK-ul citeste COGNITIVESS_API_KEY direct din .env."""
    import os
    from cognitivess._base_client import _load_env_file

    saved = os.environ.pop("COGNITIVESS_API_KEY", None)
    env = tmp_path / ".env"
    env.write_text(
        "# comentariu\n"
        "export COGNITIVESS_API_KEY=\"ssh-ed25519 from-env-file\"\n"
        "OTHER_VAR=ignored\n",
        encoding="utf-8",
    )
    try:
        cog = Cognitivess(env_file=str(env))
        assert cog.api_key == "ssh-ed25519 from-env-file"
        # cheile deja in env nu se suprascriu
        os.environ["COGNITIVESS_API_KEY"] = "explicit-wins"
        cog2 = Cognitivess(env_file=str(env))
        assert cog2.api_key == "explicit-wins"
        cog.close()
        cog2.close()
    finally:
        os.environ.pop("COGNITIVESS_API_KEY", None)
        os.environ.pop("OTHER_VAR", None)
        if saved is not None:
            os.environ["COGNITIVESS_API_KEY"] = saved


def test_env_file_missing_is_noop(tmp_path):
    import os
    saved = os.environ.pop("COGNITIVESS_API_KEY", None)
    try:
        with pytest.raises(ValueError):
            Cognitivess(env_file=str(tmp_path / "nope.env"))
    finally:
        if saved is not None:
            os.environ["COGNITIVESS_API_KEY"] = saved


def test_attrdict_access():
    d = _to_attrdict({"choices": [{"message": {"content": "hi"}}]})
    assert d.choices[0].message.content == "hi"


def test_resources_wired():
    cog = Cognitivess(api_key="ssh-ed25519 test")
    assert cog.chat.completions._client is cog
    assert cog.messages._client is cog
    assert cog.models._client is cog
    assert cog.responses._client is cog
    assert cog.base_url == "https://api.cognitivess.com/v1"
    cog.close()


def test_chat_create_body(monkeypatch):
    cog = Cognitivess(api_key="ssh-ed25519 test")
    captured = {}

    def fake_post(self, path, body, *, headers=None):
        captured["path"] = path
        captured["body"] = body
        return _to_attrdict({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(type(cog), "_post", fake_post)
    r = cog.chat.completions.create(
        model="Cognitivess-1",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=32,
        temperature=0.5,
    )
    assert captured["path"] == "/chat/completions"
    assert captured["body"]["model"] == "Cognitivess-1"
    assert captured["body"]["max_tokens"] == 32
    assert captured["body"]["temperature"] == 0.5
    assert r.choices[0].message.content == "ok"
    cog.close()


def test_messages_create_body_and_headers(monkeypatch):
    cog = Cognitivess(api_key="ssh-ed25519 test")
    captured = {}

    def fake_post(self, path, body, *, headers=None):
        captured["path"] = path
        captured["body"] = body
        captured["headers"] = headers
        return _to_attrdict({"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr(type(cog), "_post", fake_post)
    r = cog.messages.create(
        model="Cognitivess-1",
        max_tokens=64,
        system="be brief",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert captured["path"] == "/messages"
    assert captured["body"]["system"] == "be brief"
    assert captured["body"]["max_tokens"] == 64
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["headers"]["x-api-key"] == "ssh-ed25519 test"
    assert r.content[0].text == "ok"
    cog.close()


def test_sse_parse_line():
    assert _BaseClient._parse_sse_line("") is None
    assert _BaseClient._parse_sse_line(": keepalive") is None
    assert _BaseClient._parse_sse_line("data: [DONE]") == "DONE"
    parsed = _BaseClient._parse_sse_line('data: {"choices":[]}')
    assert parsed.choices == []


def test_stream_yields_chunks(monkeypatch):
    cog = Cognitivess(api_key="ssh-ed25519 test")

    def fake_stream(self, method, path, body, *, headers=None):
        assert method == "POST" and path == "/chat/completions"
        assert body["stream"] is True
        for payload in [
            {"choices": [{"delta": {"content": "Hel"}}]},
            {"choices": [{"delta": {"content": "lo"}}]},
        ]:
            yield _to_attrdict(payload)

    monkeypatch.setattr(type(cog), "_stream", fake_stream)
    out = ""
    for chunk in cog.chat.completions.create(
        model="Cognitivess-1",
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
    ):
        out += chunk.choices[0].delta.content
    assert out == "Hello"
    cog.close()


def test_async_post_is_coroutine():
    import inspect, asyncio
    cog = AsyncCognitivess(api_key="ssh-ed25519 test")
    assert inspect.iscoroutinefunction(cog._post)
    asyncio.run(cog.aclose())


def test_json_or_text_handles_empty_and_non_json():
    import httpx
    from cognitivess._base_client import _json_or_text

    empty = httpx.Response(204, content=b"")
    assert _json_or_text(empty) is None

    plain = httpx.Response(200, content=b"hello world", headers={"content-type": "text/plain"})
    assert _json_or_text(plain) == "hello world"

    js = httpx.Response(200, content=b'{"ok": true}')
    assert _json_or_text(js) == {"ok": True}


def test_stream_raises_with_error_body(monkeypatch):
    """Bug #1: pe status non-2xx in stream, mesajul de eroare trebuie sa ajunga
    la exceptie (nu se pierde prin ResponseNotRead)."""
    import httpx
    from cognitivess import AuthenticationError

    cog = Cognitivess(api_key="ssh-ed25519 test")

    error_body = b'{"error":{"message":"bad key boom","type":"invalid_request_error"}}'

    class FakeStream:
        def __init__(self, resp):
            self._resp = resp

        def __enter__(self):
            return self._resp

        def __exit__(self, *exc):
            return False

    def fake_stream(method, url, **kwargs):
        resp = httpx.Response(401, content=error_body, request=httpx.Request(method, url))
        return FakeStream(resp)

    monkeypatch.setattr(cog._http, "stream", fake_stream)

    gen = cog.chat.completions.create(
        model="Cognitivess-1", messages=[{"role": "user", "content": "hi"}], stream=True
    )
    with pytest.raises(AuthenticationError) as ei:
        list(gen)
    assert "bad key boom" in ei.value.message
    cog.close()


def test_retry_after_header_honored(monkeypatch):
    """Bug #5: Retry-After (secunde) este respectat, nu se doarme fix 2**n."""
    import httpx
    from cognitivess._base_client import _BaseClient

    seen = {"calls": 0}
    slept = []

    resp = httpx.Response(
        429,
        content=b'{"error":{"message":"slow down"}}',
        headers={"retry-after": "7"},
    )
    assert _BaseClient._retry_delay(resp, 0) == 7.0
    # fara header -> backoff in [base, base+0.25]
    d = _BaseClient._retry_delay(None, 1)
    assert 1.0 <= d <= 1.25