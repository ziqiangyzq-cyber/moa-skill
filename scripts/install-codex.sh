#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
destination="${1:-${CODEX_HOME:-$HOME/.codex}/skills/moa}"
overlay="$root/runtimes/codex"

if [ -L "$destination" ]; then
  echo "install-codex: destination must not be a symbolic link: $destination" >&2
  exit 3
fi

mkdir -p "$destination"
root_real="$(cd "$root" && pwd -P)"
destination_real="$(cd "$destination" && pwd -P)"
if [ "$destination_real" = "/" ]; then
  echo "install-codex: refusing to install over the filesystem root" >&2
  exit 3
fi
case "$destination_real" in
  "$root_real"|"$root_real"/*)
    echo "install-codex: refusing to install over the source checkout: $destination" >&2
    exit 3
    ;;
esac

copy_file() {
  local source_path="$1"
  local destination_path="$2"
  mkdir -p "$(dirname "$destination/$destination_path")"
  cp "$source_path" "$destination/$destination_path"
}

copy_tree() {
  local source_path="$1"
  local destination_path="$2"
  mkdir -p "$destination/$destination_path"
  cp -R "$source_path/." "$destination/$destination_path/"
}

copy_file "$root/.gitignore" ".gitignore"
copy_file "$root/LICENSE" "LICENSE"
copy_file "$root/moa_decision.md" "moa_decision.md"
copy_file "$root/adapters/README.md" "adapters/README.md"
copy_file "$root/docs/DESIGN.md" "docs/DESIGN.md"
copy_file "$root/bin/moa-call" "bin/moa-call"
copy_tree "$root/adapters/examples" "adapters/examples"
copy_tree "$root/prompts" "prompts"

copy_file "$overlay/README.md" "README.md"
copy_file "$overlay/SKILL.md" "SKILL.md"
copy_file "$overlay/roster.example.yaml" "roster.example.yaml"
copy_file "$overlay/agents/openai.yaml" "agents/openai.yaml"
copy_file "$overlay/adapters/codex.py" "adapters/codex.py"
copy_file "$overlay/adapters/codex.sh" "adapters/codex.sh"
copy_file "$overlay/bin/moa-preflight" "bin/moa-preflight"
copy_file "$overlay/scripts/bootstrap-local.sh" "scripts/bootstrap-local.sh"

chmod +x \
  "$destination/bin/moa-call" \
  "$destination/bin/moa-preflight" \
  "$destination/adapters/codex.py" \
  "$destination/adapters/codex.sh" \
  "$destination/scripts/bootstrap-local.sh"
find "$destination/adapters/examples" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} +

echo "Installed Codex MoA source files at $destination"
echo "Next: bash $destination/scripts/bootstrap-local.sh"
echo "Then: $destination/bin/moa-preflight $destination/roster.yaml"
