#!/usr/bin/env bash
set -euo pipefail

prompt="$(cat)"

args=(
  -p
  --output-format
  text
  --permission-mode
  bypassPermissions
)

if [ -n "${MOA_CLAUDE_MODEL:-}" ]; then
  args+=(--model "$MOA_CLAUDE_MODEL")
fi

printf '%s' "$prompt" | claude "${args[@]}" -
