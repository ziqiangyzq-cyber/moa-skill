#!/usr/bin/env bash
# MiniMax text model adapter.
#
# Contract: reads the full prompt on stdin, writes only the assistant answer on
# stdout, and exits non-zero on HTTP/API/schema errors.
#
# Credentials stay outside Git/roster.yaml:
#   MOA_MINIMAX_API_KEY   required
#   MOA_MINIMAX_API_BASE  defaults to the international API; use
#                         https://api.minimaxi.com for a mainland-China key
#   MOA_MINIMAX_MODEL     defaults to MiniMax-M3
set -euo pipefail

: "${MOA_MINIMAX_API_KEY:?export MOA_MINIMAX_API_KEY}"

api_base="${MOA_MINIMAX_API_BASE:-https://api.minimax.io}"
model="${MOA_MINIMAX_MODEL:-MiniMax-M3}"
prompt="$(cat)"

body="$(jq -n --arg model "$model" --arg prompt "$prompt" \
  '{model:$model, messages:[{role:"user", content:$prompt}]}')"

resp_file="$(mktemp)"
err_file="$(mktemp)"
trap 'rm -f "$resp_file" "$err_file"' EXIT

set +e
status="$(curl -sS -m "${MOA_HTTP_TIMEOUT:-120}" \
  -o "$resp_file" \
  -w '%{http_code}' \
  "${api_base%/}/v1/text/chatcompletion_v2" \
  -H "Authorization: Bearer $MOA_MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$body" \
  2>"$err_file")"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  echo "minimax adapter: request failed (curl exit $rc)" >&2
  sed -n '1,20p' "$err_file" >&2
  exit "$rc"
fi
case "$status" in
  2??)
    ;;
  *)
    echo "minimax adapter: HTTP $status" >&2
    exit 22
    ;;
esac

response="$(cat "$resp_file")"

api_status="$(printf '%s' "$response" | jq -r '.base_resp.status_code // 0')"
if [ "$api_status" != "0" ]; then
  echo "minimax adapter: API error code $api_status" >&2
  exit 70
fi

printf '%s' "$response" | jq -er '.choices[0].message.content | select(type == "string" and length > 0)'
