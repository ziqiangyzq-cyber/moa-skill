# Adapters

An adapter is how MoA talks to one model. The contract is deliberately tiny so you can wire
any model — an HTTP API or a local CLI — in a few lines.

## Contract

| | |
|---|---|
| **Input** | The full prompt on **stdin**. (Never as an argument — stdin is safe for prompts with quotes, newlines, and backticks, and avoids CLIs that drop long argument payloads.) |
| **Output** | The model's answer as plain text on **stdout**. No JSON envelope required. |
| **Failure** | Exit **non-zero**; put diagnostics on **stderr**. |
| **Secrets** | API keys / endpoints live **inside the adapter or its environment** — never in `roster.yaml`. |
| **Timeout & empty-check** | Handled by the *caller* (`bin/moa-call`), not the adapter. |

That's the whole contract. Invocation is always: `bin/moa-call adapters/yours.sh < prompt.txt`

## Getting started
1. Copy an example from `examples/` to `adapters/<name>.sh`.
2. Put your endpoint/model in it; export your key in your shell (or a gitignored env file).
3. `chmod +x adapters/<name>.sh`
4. Reference it from `roster.yaml`.
5. Smoke test: `echo "Say only: OK" | ./adapters/<name>.sh`

Keep adapters from **different vendors** — that is the entire point of this tool.

## Included examples

- `examples/openai-compatible.sh` — any OpenAI-compatible HTTP endpoint or proxy
- `examples/claude-code.sh` — local `claude` CLI worker
- `examples/codex-cli.sh` — local `codex exec` worker
- `examples/agy-cli.sh` — local Antigravity CLI worker (`MOA_AGY_MODEL` required)
- `examples/grok-cli.sh` — local Grok CLI worker (optional `MOA_GROK_MODEL`)
- `examples/cli-wrapper.sh` — generic local CLI skeleton

The Codex example also accepts `MOA_CODEX_EFFORT` and forwards it as the
`model_reasoning_effort` config override. This supports any effort value accepted by the
installed Codex CLI and selected model.

**AGY privacy caveat:** AGY 1.1 print mode has no prompt-file/stdin prompt option, so the
example must bridge MoA stdin to AGY's `--print <prompt>` argument. On a shared host, another
user may briefly see that argument in the process list. Do not use this adapter for confidential
prompts there; prefer a dedicated API adapter or a CLI release with prompt-file/stdin support.

If your install path came from a GitHub ZIP or another copy step that dropped executable bits,
run `bash scripts/bootstrap-local.sh` from the repo root before the first smoke test.
