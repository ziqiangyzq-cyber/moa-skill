#!/usr/bin/env bash
set -euo pipefail

prompt="$(cat)"
out_file="$(mktemp)"
trap 'rm -f "$out_file"' EXIT

args=(
  exec
  --dangerously-bypass-approvals-and-sandbox
  --skip-git-repo-check
  --output-last-message
  "$out_file"
)

if [ -n "${MOA_CODEX_MODEL:-}" ]; then
  args+=(--model "$MOA_CODEX_MODEL")
fi

if ! printf '%s' "$prompt" | codex "${args[@]}" - >/dev/null 2>&1; then
  rc=$?
  echo "codex adapter failed (exit $rc)" >&2
  exit "$rc"
fi

if [ ! -s "$out_file" ]; then
  echo "codex adapter returned empty output" >&2
  exit 5
fi

cat "$out_file"
