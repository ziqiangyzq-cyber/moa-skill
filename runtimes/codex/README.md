# MoA for Codex

This directory is the Codex-specific overlay for the shared MoA source tree.
Install it from the repository root:

```bash
bash scripts/install-codex.sh
bash "${CODEX_HOME:-$HOME/.codex}/skills/moa/scripts/bootstrap-local.sh"
"${CODEX_HOME:-$HOME/.codex}/skills/moa/bin/moa-preflight" \
  "${CODEX_HOME:-$HOME/.codex}/skills/moa/roster.yaml"
```

The installer composes a separate Codex skill at
`${CODEX_HOME:-$HOME/.codex}/skills/moa`. It does not modify or link a Claude
installation, and updates preserve `roster.yaml`, `runs/`, and custom adapters.

The published OpenAI worker reads the active Codex provider configuration and
the provider's environment-key credential. It sends a non-streaming Responses
request without tools and accepts text only from a completed response. No
endpoint, model name, or credential is embedded in the repository.

Bootstrap may create a local Claude CLI adapter when `claude` is installed.
Review `roster.yaml` before the first run and keep every vendor credential in
the environment, never in the roster.
