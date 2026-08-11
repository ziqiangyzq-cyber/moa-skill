#!/usr/bin/env bash
# Antigravity CLI worker. Configure with:
#   MOA_AGY_MODEL   required model ID from `agy models`
#   MOA_AGY_EFFORT  optional effort accepted by that model
#   MOA_AGY_BIN     optional CLI path/name (default: agy)
set -euo pipefail

: "${MOA_AGY_MODEL:?set MOA_AGY_MODEL to an ID reported by agy models}"

prompt="$(cat)"
if [ -z "${prompt//[[:space:]]/}" ]; then
  echo "agy adapter: empty prompt on stdin" >&2
  exit 6
fi

agy_bin="${MOA_AGY_BIN:-agy}"
if ! command -v "$agy_bin" >/dev/null 2>&1; then
  echo "agy adapter cannot find executable: $agy_bin" >&2
  exit 127
fi

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

# AGY 1.1 print mode requires the prompt as a CLI argument. The adapter still
# exposes the MoA stdin contract, but shared-host users should read the privacy
# warning in adapters/README.md before sending confidential prompts.
args=(
  --print
  "$prompt"
  --model
  "$MOA_AGY_MODEL"
  --output-format
  text
  --sandbox
  --disable-slash-commands
  --new-project
)

if [ -n "${MOA_AGY_EFFORT:-}" ]; then
  args+=(--effort "$MOA_AGY_EFFORT")
fi

cd "$work_dir"
"$agy_bin" "${args[@]}"
