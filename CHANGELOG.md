# Changelog

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