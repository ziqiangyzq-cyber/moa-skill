# MoA — a Mixture-of-Agents skill for hard decisions

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that turns one hard
question into a **committee of models from different vendors**, then synthesizes their answers
into a decision memo — with the disagreements and the minority view preserved, not averaged away.

It is built for **high-stakes, easy-to-disagree judgment calls** (architecture and tooling
choices, risky business or design decisions), not quick lookups. It deliberately spends several
model calls to buy a better answer.

## Why vendors, not just models

The whole value of a Mixture-of-Agents is **error independence**. Two models from the *same*
vendor share training data and RLHF, so they are blind in the same places — a same-vendor
committee is an expensive echo chamber. Models from *different* lineages (OpenAI, Anthropic,
Google, xAI…) have different blind spots, so one catches what another misses. **Lineage
diversity beats raw strength.** This skill enforces that with a preflight warning.

## How it works

```
Phase 0   Send your question to every worker — verbatim (no reframing).
          (Only add context, with your approval, when the workers can't see something.)
R1        Workers from different vendors propose in parallel, independently, blind.
Draft     The aggregator merges the proposals into a disposable strawman (not shown yet).
R2        The strawman is shown to all workers for ADVERSARIAL critique
          ("what's wrong / missing? — else NOTHING TO ADD").
Final     The aggregator folds critiques in — presenting real disagreements as forks with
          conditions, never resolving by vote count.
Review    A DIFFERENT-vendor model reviews the final merge for distortion / lineage bias.
Deliver   Decision · Why · Disagreement map · Minority view · Risks · Next step · grounded confidence.
```

Hard cap: **2 rounds.** Unresolved disagreement ships loud (both positions + conditions + low
confidence), never a fake consensus and never a silent third round.

## Design notes (honest limits)

This diversifies the *middle* (proposing + critiquing). The two ends — the question you send
and the final merge — run through one orchestrator model. Passthrough closes the first end; a
cross-vendor review closes most of the second. What remains: the merge still carries the
orchestrator's lineage, and on pure-judgment questions where every model shares a bias with no
external ground truth to probe, nothing here catches it — your own skepticism is the backstop.
These are stated plainly in `SKILL.md → Known limits`. See `docs/DESIGN.md` for the full rationale.

## Setup

1. **Install** — place this directory where your Claude Code skills live (or point your skills
   config at it). The skill is named `moa`.
2. **Bootstrap** — if you installed from a GitHub ZIP or a tool that copied plain files, run
   `bash scripts/bootstrap-local.sh` once. This restores executable bits that ZIP installs
   commonly drop, and on machines that already have both `claude` and `codex` CLIs available
   it can scaffold a minimal two-vendor local setup for you without touching existing private
   files.
3. **Roster** — `cp roster.example.yaml roster.yaml` and fill in *your own* models. Pick
   different vendors. `roster.yaml` is gitignored.
4. **Adapters** — for each model, copy an example from `adapters/examples/` to
   `adapters/<name>.sh`, set its endpoint/model, and export your API key in your environment
   (**never** in `roster.yaml`). `adapters/examples/claude-code.sh` and
   `adapters/examples/codex-cli.sh` are included for local CLI-based runs; the OpenAI-compatible
   HTTP example remains available for remote or proxy-backed workers. See `adapters/README.md`
   for the contract.
5. **Check** — `bin/moa-preflight roster.yaml` should report ≥2 distinct vendors. The
   preflight uses [PyYAML](https://pypi.org/project/PyYAML/) if installed (recommended for
   any non-trivial roster: `pip install pyyaml`); without it, it parses the simple documented
   format and refuses loudly on anything fancier rather than risk mis-reading a vendor tag.
6. **Use** — in Claude Code, write `moa <your hard question>`.

## Local quick start

If the machine already has both `claude` and `codex` CLIs working, this is enough:

```bash
bash scripts/bootstrap-local.sh
bin/moa-preflight roster.yaml
```

The bootstrap script will:

- restore executable bits on `bin/*` and example adapters
- create `adapters/claude.sh` from `adapters/examples/claude-code.sh` if `claude` is installed
- create `adapters/codex.sh` from `adapters/examples/codex-cli.sh` if `codex` is installed
- create a minimal two-vendor `roster.yaml` if one does not exist yet

Optional env vars for the local CLI adapters:

- `MOA_CLAUDE_MODEL` to force a specific Claude model
- `MOA_CODEX_MODEL` to force a specific Codex model

## Security

API keys live in your adapters / environment, never in `roster.yaml`. `roster.yaml`, `runs/`,
and common env files are gitignored. Note that any worker pointed at an external API sends your
question to that vendor — for confidential material, redact first or use only local/trusted
adapters. The skill warns you at Phase 0.

## License

MIT — see [LICENSE](LICENSE).
