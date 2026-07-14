#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

chmod +x "$root/bin/moa-call" "$root/bin/moa-preflight"
find "$root/adapters/examples" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} +
chmod +x "$root/adapters/codex.py" "$root/adapters/codex.sh"

if [ -f "$root/adapters/claude.sh" ]; then
  chmod +x "$root/adapters/claude.sh"
elif command -v claude >/dev/null 2>&1; then
  cp "$root/adapters/examples/claude-code.sh" "$root/adapters/claude.sh"
  chmod +x "$root/adapters/claude.sh"
  echo "Created adapters/claude.sh from the local Claude CLI example."
fi

if [ ! -f "$root/roster.yaml" ]; then
  cp "$root/roster.example.yaml" "$root/roster.yaml"
  chmod 600 "$root/roster.yaml"
  echo "Created roster.yaml from the Codex two-vendor example."
fi

echo "Bootstrap complete."
echo "Next: $root/bin/moa-preflight $root/roster.yaml"
