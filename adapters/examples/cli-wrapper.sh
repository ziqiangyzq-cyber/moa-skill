#!/usr/bin/env bash
# Skeleton adapter for a model exposed as a local CLI (e.g. a vendor's `foo-cli`, a
# `codex`/`gemini`/`llm` style tool). Adjust the invocation on the marked line.
#
# Contract: reads the full prompt on stdin, writes the answer on stdout, exits non-zero on error.
# Keep any model/version/flags and keys inside this script or its env — never in roster.yaml.
set -euo pipefail

prompt="$(cat)"

# ── EDIT THIS LINE for your CLI. Feed the prompt on stdin, keep output SHORT-form. ──
# Examples:
#   answer="$(printf '%s' "$prompt" | your-cli --quiet)"
#   answer="$(printf '%s' "$prompt" | llm -m your-model)"
answer="$(printf '%s' "$prompt" | your-cli-here)"

# Some CLIs print session/log noise before the real answer — trim to the payload if needed,
# e.g. `answer="$(printf '%s' "$answer" | sed -n '/=== ANSWER ===/,$p')"`.

printf '%s\n' "$answer"
