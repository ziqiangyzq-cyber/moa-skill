#!/usr/bin/env bash
# Grok CLI worker. Configure with:
#   MOA_GROK_MODEL  optional model ID from `grok models` (uses CLI default if unset)
#   MOA_GROK_BIN    optional CLI path/name (default: grok)
set -euo pipefail

grok_bin="${MOA_GROK_BIN:-grok}"
if ! command -v "$grok_bin" >/dev/null 2>&1; then
  echo "grok adapter cannot find executable: $grok_bin" >&2
  exit 127
fi

work_dir="$(mktemp -d)"
prompt_file="$work_dir/prompt.txt"
out_file="$work_dir/output.txt"
err_file="$work_dir/stderr.txt"
trap 'rm -rf "$work_dir"' EXIT
cat >"$prompt_file"

if [ ! -s "$prompt_file" ]; then
  echo "grok adapter: empty prompt on stdin" >&2
  exit 6
fi

args=(
  --prompt-file
  "$prompt_file"
  --output-format
  plain
  --verbatim
  --disable-web-search
  --no-memory
  --no-subagents
  --tools
  ""
  --permission-mode
  dontAsk
  --cwd
  "$work_dir"
)

if [ -n "${MOA_GROK_MODEL:-}" ]; then
  args+=(--model "$MOA_GROK_MODEL")
fi

set +e
"$grok_bin" "${args[@]}" >"$out_file" 2>"$err_file"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  cat "$err_file" >&2
  echo "grok adapter failed (exit $rc)" >&2
  exit "$rc"
fi
if [ ! -s "$out_file" ]; then
  cat "$err_file" >&2
  echo "grok adapter returned empty output" >&2
  exit 5
fi

cat "$out_file"
