---
name: moa
description: >-
  Use when the user writes "moa QUESTION" or explicitly asks for a
  multi-model committee on a hard, high-stakes, easy-to-disagree architecture,
  tooling, business, design, regulatory, or strategy decision where independent
  vendor perspectives justify several model calls.
---

# MoA — Mixture-of-Agents decision support

## What this is
A committee protocol, not a single model. It combines the *complementary* strengths of
several heterogeneous models on one hard question. Its value comes from **error
independence across vendors** — models from different lineages have different blind
spots, so one catches what another misses. Same-vendor models share blind spots and
defeat the whole purpose (see the preflight check).

**It diversifies the middle (proposing + critiquing). Be honest about the two ends:**
the question you send and the final merge both run through *one* model (the orchestrator).
The design closes the first end with **raw passthrough** and the second with a
**cross-vendor review of the merge**. Neither is free of the orchestrator's own lineage —
that residual is stated in "Known limits" and is real.

## When to fire
- User writes `moa <question>` or asks for a "committee / multi-model / MoA" take.
- The question is a genuine hard judgment call worth N model bills. If it looks quick or
  low-stakes, say so and offer a single-model answer first — don't spend the committee by reflex.

## Cost reality (tell the user before a big run)
One run ≈ **2N+ token-heavy calls**: N proposals + a draft (reads all N) + N critiques
(each reads the draft) + a final merge (reads N critiques) + 1 cross-vendor review.
With N=3 that is ~9 model calls and can take several minutes. There is no cache reuse.
Fire it on questions that are actually worth that.

---

## The procedure

### Codex-local execution
- Resolve `SKILL_ROOT` as the directory containing this `SKILL.md`; run all relative paths from there.
- Use only file-backed adapters from `roster.yaml`. Do not treat Codex collaboration subagents as vendor diversity unless the runtime exposes a real different-vendor model.
- Invoke every worker through `bin/moa-call` and launch independent R1/R2 calls concurrently with the active tool's parallel mechanism.
- The current Codex session performs the aggregator role; `roster.yaml` records its vendor so `final_review` can enforce a different lineage.

### Preflight (once per run)
1. Read `roster.yaml` (fall back to `roster.example.yaml` only for a dry run; a real run
   needs the user's own roster). Run `bin/moa-preflight roster.yaml`.
2. **Honor its warnings out loud.** If it reports fewer than 2 distinct vendors among the
   active propose/critique slots, tell the user the error-independence premise is void and
   they are paying N× for correlated answers — proceed only if they insist.
3. If `aggregator` and `final_review` share a vendor, warn that the End-B cross-check is void.

### Phase 0 — the question (PASSTHROUGH BY DEFAULT)
- **Default: send the user's raw question, byte-for-byte, to every worker.** Do NOT
  paraphrase or "improve" it. There is no reframing step to bias. This is the rule.
- **Exception — context-inline only (never a reframe):** if the question points at private/
  local material the workers cannot see ("this contract", "the X situation", an attached
  file, a prior turn), build a brief that is **the user's raw question verbatim + an
  appended CONTEXT block** containing that material. The question text is never altered;
  the brief only *adds*. **Show the user the context block for approval before firing.**
- **If the question is ambiguous/underspecified: ask the user to clarify.** Do not silently
  pick an interpretation and bake it into a brief. Clarification ≠ context-inlining.
- **Privacy gate:** if the brief would carry client-confidential / contract / credential
  material and any worker egresses to an external vendor, redact it first or restrict this
  run to local/trusted adapters. Warn the user.

### R1 — propose (parallel, independent, blind)
- For each worker with role `propose`, send the Phase-0 input through its adapter using
  `bin/moa-call <adapter> < prompt`. Use `prompts/proposer.md` as the wrapper. Run independent
  adapter calls concurrently with the active tool's parallel mechanism; preserve each worker's
  stdout and exit status separately.
- Each proposal must contain: **claim / reasoning / confidence / "what would change my mind"**.
- **Integrity gate:** `moa-call` fails non-zero on empty/timeout. If a worker fails, do NOT
  silently proceed at normal confidence. Record "N/total responded", cap the final
  confidence, and if the failure collapsed the roster to a single vendor, say so explicitly.
- Save every raw proposal to the run dir (see Audit).

### Draft synthesis (current Codex session = the `aggregator` slot)
- Using `prompts/aggregator.md`, the current Codex session produces a DRAFT synthesis of the N proposals.
- **Do not show the draft to the user yet.** It is a disposable strawman.

### R2 — adversarial critique (default-ON)
- Show the draft to **all** workers, **stripped of authority** — present it as "a candidate
  answer, possibly wrong", authored anonymously. Use `prompts/critique.md`.
- For the external-vendor worker via `moa-call`, **compress the draft to the disagreement
  crux first** — do not stream the full long draft into a CLI that drops long inputs.
- Each critic finds ERRORS / OMISSIONS / defends an overruled position / flags
  training-consensus-only claims, or replies exactly `NOTHING TO ADD`.
- **Shared-blind-spot step:** for any factual / regulatory / numeric question, do NOT rely on
  the models asking themselves "did we all miss something". Run an **out-of-model probe** —
  a web search, an authoritative source/DB lookup, or ask the user — and fold the result in.

### Final synthesis + cross-vendor review (the End-B fix)
- Fold the critiques into the FINAL answer. Instruction to yourself: **the draft was a
  disposable strawman by an anonymous author; critiques win ties; judge by content, not source.**
  For a genuine substantive disagreement, **default to presenting both positions + the
  condition under which each holds** — only adjudicate when you can name a concrete reasoning
  defect in one side. Never resolve by vote count.
- Then send the FINAL answer + the raw disagreements it claims to resolve to a
  **different-vendor** worker (`final_review` slot) via `prompts/final-review.md`:
  "what did this merge distort, drop, or lineage-bias? else NOTHING TO ADD."
  If it flags real distortion, do **one** bounded revision. This is a check on the final,
  **not** a third round — the 2-round cap stays intact.

### Stop rule
**Hard cap at 2 rounds. No third round, ever.** If a disagreement is still unresolved at the
cap, ship it LOUD: present both positions, the condition under which each is right, and a
**grounded** low confidence. Do not fake convergence and do not spin up another round.

### Deliver
Use `moa_decision.md` shape:
**Decision / Why / Disagreement map / Strongest minority argument (cleaned, not raw) /
Risks & reversibility / Next step / Confidence (grounded) + what would flip it.**
Offer `short` / `standard` / `deep` length; default `standard`.
Confidence is **grounded in observable signals** — number of substantive disagreements,
reversibility of the decision, density of "what-would-flip" triggers — NOT a self-reported
probability. Never lead with a vibes number.

### Audit
Before writing, run `umask 077`, create `runs/<timestamp>/` with mode `0700`, and keep every
artifact at mode `0600`. Store only the redacted Phase-0 input for confidential work; never
persist credentials or unredacted source documents. The run dir contains: the Phase-0 input
actually sent, every raw R1 and R2 response, the draft, the final, and a one-line `delta` = did
R2/​review change the decision vs the draft? State the run path at delivery. Do not auto-delete
audit records; the user decides retention because deletion is irreversible. (If final ≈ draft
over many runs, R2 is only ratifying — revisit whether it earns its cost.)

---

## Known limits (do not pretend these are solved)
1. **Aggregator lineage.** The merge runs on the orchestrator's model, so even with diverse
   workers the synthesis carries that lineage's lens. The cross-vendor review mitigates but
   does not remove it.
2. **Shared blind spots on pure-judgment questions.** External probes only rescue
   factual/regulatory questions. If every model shares a training bias on a pure-strategy
   question with no ground truth to probe, nothing here catches it — the user's own
   skepticism is the only backstop.
3. **Confidence is a grounded heuristic, not a calibrated probability.**
4. **Self-declared vendor tags are trusted.** The preflight can't verify a stranger mislabeled
   a model's vendor; it catches honest mistakes, not deception.

## Retires
This supersedes any ad-hoc "moa mode" behavior note. Use this skill.
