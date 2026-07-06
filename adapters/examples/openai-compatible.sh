#!/usr/bin/env bash
# Generic adapter for any OpenAI-compatible /chat/completions endpoint
# (OpenAI, Groq, Together, OpenRouter, a local vLLM/Ollama gateway, a self-hosted proxy...).
#
# Contract: reads the full prompt on stdin, writes the answer on stdout, exits non-zero on error.
# Configure via env (export these in your shell or a gitignored env file — NOT in roster.yaml):
#   MOA_API_BASE   e.g. https://api.openai.com/v1   (default)
#   MOA_API_KEY    your key  (required)
#   MOA_MODEL      e.g. gpt-4o / gpt-5.5 / llama-3.3-70b  (required)
set -euo pipefail

: "${MOA_API_KEY:?export MOA_API_KEY}"
: "${MOA_MODEL:?export MOA_MODEL}"
base="${MOA_API_BASE:-https://api.openai.com/v1}"

prompt="$(cat)"

# jq builds a correctly-escaped JSON body from the raw prompt (handles quotes/newlines).
body="$(jq -n --arg m "$MOA_MODEL" --arg p "$prompt" \
  '{model:$m, messages:[{role:"user", content:$p}]}')"

resp="$(curl -sS --fail-with-body -m "${MOA_HTTP_TIMEOUT:-120}" \
  "$base/chat/completions" \
  -H "Authorization: Bearer $MOA_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$body")"

# Extract the assistant text; fail loudly if the shape is unexpected.
echo "$resp" | jq -er '.choices[0].message.content'
