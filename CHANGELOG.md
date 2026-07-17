# Changelog

## 0.1.7

### Added
- **Client-type identification header.** The SDK now sends `X-Cognitivess-Client: sdk`
  on every request, so the gateway can distinguish SDK users from CLI / direct Claude
  Code users in the admin dashboard. The gateway reads this header with priority over
  `User-Agent`.

## 0.1.6

### Fixed
- **Streaming now retries retryable status codes.** Previously only non-streaming
  requests retried on `429/500/502/503/504/408/409`; a streaming request that got
  one of these at connection time failed immediately (1 attempt regardless of
  `max_retries`). `_stream` (sync + async) now retries the same set as `_request`,
  honoring `Retry-After`. Retry happens **only before the first `yield`**, so a
  transient failure at stream open is retried safely with no risk of duplicating
  output to the consumer.
- **Mid-stream connection errors now surface as `APIConnectionError`** (part of
  the `CognitivessError` hierarchy) instead of leaking as a raw `httpx` exception.
  They are never retried (output may already have been produced).
- Timeouts (open or mid-stream) are still not retried, matching `_request`.

### Tests
- Added regression tests for streaming retry on retryable status, no-retry on
  non-retryable status, and no-retry / no-duplicate after the first chunk.

## 0.1.5

### Docs
- Refreshed README: the feature list now covers `iter_text()`, per-request
  `timeout`, `models.retrieve()`, `COGNITIVESS_BASE_URL` from env, `Retry-After`,
  and the `py.typed` marker; added a CHANGELOG link and clarified that
  `iter_text()` streams under the hood (no `stream=True` needed).

## 0.1.4

### Added
- **`COGNITIVESS_BASE_URL` from env.** `base_url` now resolves from
  env / `.env` as a fallback (explicit `base_url=` still wins), so self-hosted/dev
  setups need no `base_url=` in code.
- **`iter_text()` streaming helper** on `chat.completions` — yields only the
  content strings, skipping metadata / empty-choice chunks. Sync (`for text in …`)
  and async (`async for text in …`) aware. Removes the
  `if chunk.choices: getattr(delta, "content", None)` boilerplate.
- **Per-request `timeout`.** `create(..., timeout=30)` overrides the client
  timeout for a single call (not sent in the JSON body). Available on chat,
  messages, responses, and `models.retrieve`.
- **`models.retrieve(id)`** — `GET /models/{id}` for a single model.
- **`py.typed`** marker shipped in the wheel so IDEs/type-checkers treat the
  package as typed.

### Changed
- `.env` is now loaded early (before resolving both `api_key` and `base_url`),
  so `COGNITIVESS_BASE_URL` in `.env` works too. Existing env vars are still
  never overridden.

## 0.1.3

### Added
- **Automatic `.env` loading.** `Cognitivess()` now reads a `.env` file from the
  cwd as a fallback when `COGNITIVESS_API_KEY` isn't already in the environment —
  no `python-dotenv` / `load_dotenv()` needed. Existing env vars are never
  overridden. Control via the new `env_file` constructor argument (default
  `".env"`; pass `None` to disable, or a path to point elsewhere). Built-in
  parser, so the SDK stays zero-heavy-deps (`httpx` only).

### Tests
- Added tests for `.env` fallback, no-override behavior, and missing-file no-op.

## 0.1.2

### Fixed
- **Streaming error body no longer lost.** On a non-2xx status during `stream=True`,
  the SDK now reads the response body before raising, so the real gateway error
  message reaches the exception instead of a generic `reason_phrase` (previously
  `httpx.ResponseNotRead` was swallowed by the error parser).
- **Stream no longer killed by reasoning pauses.** HTTP timeout now uses
  `httpx.Timeout(timeout, connect=10.0)` so a long gap between SSE events
  (reasoning / tool-use on Cognitivess-1) does not raise `APITimeoutError`
  mid-stream.
- **Non-JSON / empty success bodies no longer raise.** A `200` with an empty or
  `text/plain` body returns `None` / the raw text instead of bubbling a raw
  `JSONDecodeError` outside the `CognitivessError` hierarchy.
- **`Retry-After` honored on 429.** Retries now respect the `Retry-After`
  header (seconds or HTTP-date) and use jittered exponential backoff as fallback.
- **Mojibake** in `version.py` comment fixed.
- Removed unused imports (`Iterator`, `Optional`).

### Tests
- Added regression tests for streaming error propagation, non-JSON success
  bodies, and `Retry-After` handling.

## 0.1.1

- Initial release: sync + async clients, chat / messages / models / responses
  resources, SSE streaming, typed exceptions, retry with backoff.