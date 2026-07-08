#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

chmod +x "$root/bin/moa-call" "$root/bin/moa-preflight"
find "$root/adapters/examples" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} +

if [ -f "$root/adapters/claude.sh" ]; then
  chmod +x "$root/adapters/claude.sh"
elif command -v claude >/dev/null 2>&1; then
  cp "$root/adapters/examples/claude-code.sh" "$root/adapters/claude.sh"
  chmod +x "$root/adapters/claude.sh"
  echo "Created adapters/claude.sh from local Claude CLI example."
fi

if [ -f "$root/adapters/codex.sh" ]; then
  chmod +x "$root/adapters/codex.sh"
elif command -v codex >/dev/null 2>&1; then
  cp "$root/adapters/examples/codex-cli.sh" "$root/adapters/codex.sh"
  chmod +x "$root/adapters/codex.sh"
  echo "Created adapters/codex.sh from local Codex CLI example."
fi

if [ ! -f "$root/roster.yaml" ]; then
  if [ -f "$root/adapters/claude.sh" ] && [ -f "$root/adapters/codex.sh" ]; then
    cat >"$root/roster.yaml" <<'EOF'
workers:
  - name: w-codex
    vendor: openai
    adapter: adapters/codex.sh
    role: [propose, critique]

  - name: w-claude
    vendor: anthropic
    adapter: adapters/claude.sh
    role: [propose, critique, aggregate]

aggregator: w-claude
final_review: w-codex
EOF
    echo "Created roster.yaml for a local Claude + Codex two-vendor setup."
  else
    cp "$root/roster.example.yaml" "$root/roster.yaml"
    echo "Created roster.yaml from roster.example.yaml."
  fi
fi

echo "Bootstrap complete."
echo "Next: $root/bin/moa-preflight $root/roster.yaml"
