# cognitivess — Python SDK

Official Python SDK for the **CognitivessAI** API. The platform is
OpenAI- **and** Anthropic-compatible, so this SDK gives you both ergonomics in
one package, talking to model **Cognitivess-1**.

```bash
pip install cognitivess
```

* Sync **and** async clients (`Cognitivess` / `AsyncCognitivess`)
* Streaming (SSE) for chat, messages and responses
* Structured Outputs (`response_format`) pass-through
* Typed exceptions, retries with backoff (honors `Retry-After`), timeout control
* Reads `.env` automatically (no `python-dotenv` dependency)
* Zero heavy deps — only `httpx`

## Setup

Generate an API key in your CognitivessAI dashboard (looks like
`ssh-ed25519 AAAA...`). It's shown only once. Then either pass it explicitly,
export it, **or** put it in a `.env` file — the SDK reads `.env` automatically
(no `python-dotenv` / `load_dotenv()` needed):

```bash
export COGNITIVESS_API_KEY="ssh-ed25519 AAAA..."
```

```dotenv
# .env  (in your project root / cwd)
COGNITIVESS_API_KEY=ssh-ed25519 AAAA...
```

The `.env` fallback only fills in variables that aren't already set in the
environment, so explicit env vars or `api_key=` always win. Disable it with
`Cognitivess(env_file=None)`, or point elsewhere with
`Cognitivess(env_file="config/.env")`.

## Quickstart

### OpenAI style — chat completions

```python
from cognitivess import Cognitivess

cog = Cognitivess()  # reads COGNITIVESS_API_KEY

resp = cog.chat.completions.create(
    model="Cognitivess-1",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ],
    max_tokens=128,
    temperature=0.7,
)
print(resp.choices[0].message.content)
```

### Anthropic style — messages

```python
msg = cog.messages.create(
    model="Cognitivess-1",
    max_tokens=128,
    system="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(msg.content[0].text)
```

### Streaming

```python
# sync
for chunk in cog.chat.completions.create(
    model="Cognitivess-1",
    messages=[{"role": "user", "content": "Count to 5."}],
    max_tokens=64,
    stream=True,
):
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

```python
# async
import asyncio
from cognitivess import AsyncCognitivess

async def main():
    async with AsyncCognitivess() as cog:
        async for chunk in cog.chat.completions.create(
            model="Cognitivess-1",
            messages=[{"role": "user", "content": "Count to 5."}],
            max_tokens=64,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)

asyncio.run(main())
```

### Structured Outputs

```python
resp = cog.chat.completions.create(
    model="Cognitivess-1",
    messages=[{"role": "user", "content": "I spent $120 on dinner and $45 on supplies."}],
    max_tokens=512,
    temperature=0.1,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "expenses",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "amount": {"type": "number"},
                            },
                            "required": ["description", "amount"],
                            "additionalProperties": False,
                        },
                    },
                    "total": {"type": "number"},
                },
                "required": ["items", "total"],
                "additionalProperties": False,
            },
        },
    },
)
print(resp.choices[0].message.content)  # JSON string
```

### Responses API

```python
r = cog.responses.create(
    model="Cognitivess-1",
    input="Say hi in one word.",
    max_output_tokens=16,
)
print(r.output_text)
```

### List models

```python
print(cog.models.list().data[0].id)
```

## Configuration

```python
cog = Cognitivess(
    api_key="...",            # optional, defaults to COGNITIVESS_API_KEY
    base_url="https://api.cognitivess.com/v1",  # override for self-hosted/dev
    timeout=60.0,             # seconds
    max_retries=2,            # retries on 429/5xx/conn errors, with backoff
    default_headers={"X-Tag": "prod"},  # merged into every request
    env_file=".env",          # auto-load .env (default); None to disable
)
```

## Error handling

```python
from cognitivess import AuthenticationError, RateLimitError, APIStatusError, APITimeoutError

try:
    cog.chat.completions.create(model="Cognitivess-1", messages=[...], max_tokens=64)
except AuthenticationError as e:    # 401 — bad/revoked key
    print("auth:", e.message, e.status_code)
except RateLimitError as e:         # 429 — rate limit / credits
    print("rate:", e.message)
except APITimeoutError:             # timeout
    ...
except APIStatusError as e:         # any other non-2xx
    print("status:", e.status_code, e.message)
```

## Notes

* This package is the **SDK library**. The `cognitivess` CLI (installed via
  `curl | sh`) is a separate tool; installing this SDK does not register a
  `cognitivess` console command, so the two coexist without conflict.
* `base_url` already includes `/v1`. The SDK calls `/chat/completions`,
  `/messages`, `/models`, `/responses` relative to it. For self-hosted/dev,
  point it at e.g. `http://localhost:8000/v1`.
* Responses objects are attribute-accessible (`resp.choices[0].message.content`)
  via a light wrapper — no Pydantic dependency.

## License

MIT