#!/usr/bin/env bash
set -euo pipefail

prompt="$(cat)"
work_dir="$(mktemp -d)"
out_file="$work_dir/last-message.txt"
trap 'rm -rf "$work_dir"' EXIT

args=(
  exec
  --sandbox
  read-only
  --ephemeral
  --ignore-user-config
  --ignore-rules
  --skip-git-repo-check
  --cd
  "$work_dir"
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
