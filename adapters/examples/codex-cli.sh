#!/usr/bin/env bash
set -euo pipefail

prompt="$(cat)"
work_dir="$(mktemp -d)"
out_file="$work_dir/last-message.txt"
err_file="$work_dir/stderr.txt"
trap 'rm -rf "$work_dir"' EXIT

codex_bin="${MOA_CODEX_BIN:-codex}"
if ! command -v "$codex_bin" >/dev/null 2>&1; then
  echo "codex adapter cannot find executable: $codex_bin" >&2
  exit 127
fi

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

set +e
printf '%s' "$prompt" | "$codex_bin" "${args[@]}" - >/dev/null 2>"$err_file"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  cat "$err_file" >&2
  echo "codex adapter failed (exit $rc)" >&2
  exit "$rc"
fi

if [ ! -s "$out_file" ]; then
  echo "codex adapter returned empty output" >&2
  exit 5
fi

cat "$out_file"
