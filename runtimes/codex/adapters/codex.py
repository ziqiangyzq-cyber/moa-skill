#!/usr/bin/env python3
"""Tool-free OpenAI Responses worker using the active Codex provider config."""

from __future__ import annotations

import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path


def die(message: str, code: int) -> None:
    print(f"codex.py: {message}", file=sys.stderr)
    raise SystemExit(code)


prompt = sys.stdin.read()
if not prompt.strip():
    die("empty prompt on stdin", 6)

config_path = Path(
    os.environ.get("CODEX_CONFIG_PATH", Path.home() / ".codex" / "config.toml")
).expanduser()
try:
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)
    provider_name = config["model_provider"]
    provider = config["model_providers"][provider_name]
except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
    die(f"cannot load provider from {config_path}: {exc}", 3)

base_override = os.environ.get("MOA_OPENAI_BASE")
key_override = os.environ.get("MOA_OPENAI_API_KEY")
if base_override and not key_override:
    die("MOA_OPENAI_BASE requires a matching MOA_OPENAI_API_KEY", 3)

base_url = base_override or provider.get("base_url")
model = (
    os.environ.get("MOA_OPENAI_MODEL")
    or os.environ.get("MOA_CODEX_MODEL")
    or config.get("model")
)
env_key = provider.get("env_key")
api_key = key_override
if not api_key and env_key:
    api_key = os.environ.get(env_key)

if not base_url:
    die("provider has no base_url; set MOA_OPENAI_BASE", 3)
if not model:
    die("no model configured; set MOA_OPENAI_MODEL", 3)
if not api_key:
    die(f"API key is not set in {env_key or 'MOA_OPENAI_API_KEY'}", 3)
if provider.get("wire_api") not in (None, "responses"):
    die("active Codex provider is not configured for the Responses API", 3)

try:
    max_output_tokens = int(os.environ.get("MOA_OPENAI_MAX_OUTPUT_TOKENS", "8192"))
    http_timeout = float(os.environ.get("MOA_HTTP_TIMEOUT", "180"))
except ValueError as exc:
    die(f"invalid numeric setting: {exc}", 3)

request_body = {
    "model": model,
    "input": [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}],
        }
    ],
    "reasoning": {
        "effort": os.environ.get(
            "MOA_OPENAI_EFFORT", os.environ.get("MOA_CODEX_EFFORT", "high")
        )
    },
    "stream": False,
    "store": False,
    "max_output_tokens": max_output_tokens,
}
request = urllib.request.Request(
    f"{base_url.rstrip('/')}/responses",
    data=json.dumps(request_body).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=http_timeout) as response:
        raw_response = response.read()
except urllib.error.HTTPError as exc:
    raw_error = exc.read().decode("utf-8", errors="replace")
    try:
        message = json.loads(raw_error).get("error", {}).get("message") or raw_error
    except json.JSONDecodeError:
        message = raw_error
    die(f"Responses API HTTP {exc.code}: {message[:500]}", 7)
except (urllib.error.URLError, TimeoutError) as exc:
    die(f"Responses API request failed: {exc}", 4)

try:
    payload = json.loads(raw_response)
except json.JSONDecodeError as exc:
    die(f"Responses API returned invalid JSON: {exc}", 5)

if payload.get("error"):
    error = payload["error"]
    message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
    die(f"Responses API error: {message[:500]}", 7)

status = payload.get("status")
if status != "completed":
    details = payload.get("incomplete_details")
    reason = details.get("reason") if isinstance(details, dict) else None
    suffix = f" ({reason})" if reason else ""
    die(f"Responses API returned non-completed status {status!r}{suffix}", 5)

text = payload.get("output_text")
if not isinstance(text, str):
    parts = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    text = "".join(parts)

if not text or not text.strip():
    die("Responses API returned no output text", 5)
sys.stdout.write(text)
