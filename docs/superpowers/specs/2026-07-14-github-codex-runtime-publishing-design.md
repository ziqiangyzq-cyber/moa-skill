# GitHub Codex runtime publishing design

## Goal

Make the tested Codex MoA runtime reproducible from
`ziqiangyzq-cyber/moa-skill` while preserving the existing Claude-oriented root
skill and keeping private runtime state out of Git.

The published source must contain both integrity fixes:

1. cancelling or timing out `moa-call` cleans up the complete adapter process
   group; and
2. the Codex Responses adapter accepts output only when the top-level response
   status is `completed`.

## Selected approach

Keep the repository root as the shared, Claude-oriented skill and add a
`runtimes/codex/` overlay plus an allowlist-based installer.

- Shared code remains at the repository root. The process supervisor in
  `bin/moa-call` is runtime-neutral and is fixed there once for every install.
- Codex-only files live under `runtimes/codex/`. The overlay contains Codex
  skill instructions, UI metadata, strict preflight, bootstrap behavior, roster
  example, and the tool-free Responses adapter.
- `scripts/install-codex.sh` composes a Codex installation from an explicit
  allowlist of shared files and then applies the overlay.

Rejected alternatives:

- Patch only the installed `~/.codex/skills/moa` copy: already tested, but a
  reinstall loses the fixes.
- Make the root skill conditional on the orchestrator runtime: one mutable
  configuration would couple Claude and Codex again.
- Publish only two loose patched files: small, but does not provide a reliable
  path from GitHub to a complete Codex installation.

## Repository layout

The change adds or modifies these source-owned units:

- `bin/moa-call`: shared Python process-group supervisor reached through shell
  `exec`.
- `runtimes/codex/`: managed Codex overlay files copied into an installed skill.
- `scripts/install-codex.sh`: installer with an optional destination argument;
  default destination is `${CODEX_HOME:-$HOME/.codex}/skills/moa`.
- `tests/test_moa_call.py`: shared timeout and cancellation regressions.
- `tests/test_codex_adapter.py`: local-loopback Responses integrity regression.
- `tests/test_codex_install.py`: installation composition and preservation
  checks.
- `README.md`: separate Claude and Codex installation instructions.

The overlay is source code, not private state. It must not contain endpoints,
credential values, run artifacts, or a real `roster.yaml`.

## Installer contract

The installer copies only named public paths. It never copies `.git/`, local
`runs/`, a real `roster.yaml`, environment files, or root `adapters/*.sh`.

For an existing destination it may replace repository-managed files such as
`SKILL.md`, `bin/moa-call`, `bin/moa-preflight`, and
`adapters/codex.py`. It must preserve:

- `roster.yaml`;
- `runs/` and every artifact below it; and
- custom adapter files that are not part of the Codex overlay.

The installer does not call models and does not automatically run bootstrap.
It prints the bootstrap and preflight commands needed to finish a new install.
This keeps installation deterministic and makes the test suite independent of
which model CLIs happen to be installed on the host.

## Runtime behavior

`moa-call` validates the adapter and requires Python 3, then replaces its shell
PID with a Python supervisor. The supervisor starts the adapter in a new
session, captures stdout for the existing non-empty-output check, and forwards
stderr. Timeout, `SIGINT`, and `SIGTERM` signal the adapter process group,
provide a one-second cleanup window, and use `SIGKILL` only for survivors.

The Codex Responses adapter sends a non-streaming, non-stored request without a
`tools` field. Before output extraction it requires `status == "completed"`.
Missing, incomplete, or unexpected status values exit non-zero with empty
stdout; an incomplete reason may be included in stderr.

## Verification

All verification is deterministic and uses no real credentials or model calls.

- A local fake Responses server proves that partial text from an incomplete
  response is rejected.
- A heartbeat adapter proves that direct `SIGTERM` cancellation stops its
  process group and returns `143`.
- Existing success, timeout cleanup, empty-output, and adapter-failure contracts
  remain covered.
- A temporary destination proves that the installer creates the expected Codex
  runtime while preserving private roster, run, and custom-adapter sentinels.
- Bash syntax, Python compilation, skill validation, and Codex preflight run on
  the composed temporary installation.

## Publication

Development starts from the current remote `main` on an `agent/` branch. Only
the intended public source, tests, and design/plan records are staged. The
branch is pushed normally and opened as a Draft PR; `main` is not force-pushed.

## Acceptance criteria

- A clean checkout can compose a valid Codex MoA skill without manual source
  patching.
- Re-running the installer does not overwrite private runtime state.
- Both integrity regressions fail against the old behavior and pass against the
  published implementation.
- The root Claude skill remains usable and does not share mutable runtime state
  with the installed Codex skill.
- The Git diff contains no private adapters, roster, run artifacts, endpoints,
  or credentials.
