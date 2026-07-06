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
