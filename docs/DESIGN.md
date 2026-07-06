# Design rationale

This skill was designed by running a Mixture-of-Agents on itself: a committee of models from
different vendors proposed, critiqued, and synthesized the design over three iterations, with a
final adversarial review each round. What follows is why it ended up the shape it is — including
the ideas that were tried and rejected, so you don't re-add them.

## The core claim

MoA's value is **error independence**, not model count and not model strength. Averaging helps
only when the things you average are wrong in *different* places. Two same-vendor models share
training data and RLHF; their errors correlate; averaging them entrenches a shared mistake
instead of cancelling it. So the load-bearing design rule is **vendor/lineage diversity**, and
the load-bearing failure mode is a **correlated blind spot** — the whole committee confidently
missing the same thing. Everything below follows from that.

## What we dropped, and why

**Multi-layer MoA (the original Together-AI architecture).** The published design stacks layers
of N proposers→N aggregators to make *weak* open-source models rival a strong one, via iterative
denoising and fragment reassembly. Weak rosters need *many* layers precisely because the
aggregator is also weak and can't denoise in one pass. A frontier, cross-vendor roster converges
in ~2 rounds; extra layers then only homogenize — sanding off the sharp, correct outlier that was
the reason to ask a diverse committee. So: **one propose layer, one critique round, hard cap at 2.**

**Deciding layer count by "are my models weak or strong."** Wrong axis, and it drifts as models
change. The real axis is "does the next pass add independent information, or just average toward
consensus?" — which depends on roster *diversity*, not strength. We don't classify models at all.

**A generic third round.** R2 already contains one re-synthesis; a generic R3 mostly churns and,
among convergent models, manufactures false agreement. When R2 leaves something unresolved we
either run a *targeted* out-of-model probe (for factual/regulatory questions) or **ship the
disagreement loud** — both positions, the condition each holds under, and a low confidence.

**"Show the merged answer back to everyone for iterative refinement."** Tempting — the user
originally wanted it — but shown a polished consensus, models anchor and rubber-stamp, and the
lone correct dissenter capitulates. That is regression-to-the-mean manufactured on purpose. The
fix is not to hide the draft (that discards blind-spot coverage) but to **strip its authority**
(present it as an anonymous, possibly-wrong candidate) and frame R2 **adversarially** ("find what's
wrong / else NOTHING TO ADD"). The `NOTHING TO ADD` escape hatch is load-bearing: it removes the
pressure to manufacture fake refinements, which is the actual mechanism of drift.

## The two ends

MoA diversifies the *middle* (proposing + critiquing). Both *ends* run through one orchestrator
model, and diversity in the middle cannot rescue a bad frame at the start or a lineage-biased
merge at the end.

- **Start (the question).** A single model rewriting your question into a "brief" is the highest-
  leverage single point of failure: if it mis-frames, every worker answers the wrong question,
  they agree (on the wrong thing), and you get confident garbage. Fix: **passthrough by default** —
  send the raw question verbatim; never paraphrase. The only allowed brief is *your words verbatim +
  an appended context block* for material the workers can't see, shown to you for approval first.
  This closes the start end.
- **End (the merge).** One model still decides what survives synthesis — an unguarded lineage bias.
  We don't move synthesis to a weaker model to buy diversity (a bad trade — the merge needs the
  strongest instruction-follower). Instead a **different-vendor model reviews the final merge** for
  distortion, dropped points, and lineage bias. It's a one-call check on the output, not a new round.

Residual, stated honestly: the merge still carries the orchestrator's lineage, and on pure-judgment
questions with no external ground truth to probe, a shared bias is uncatchable. The skill says so.

## Other decisions worth keeping

- **The aggregator does not grade its own homework blindly.** The draft is framed to the finalizer
  as a *disposable strawman by an anonymous author*; critiques win ties. (The full fix — a different
  model finalizes than drafts — is deferred; the strawman framing is the cheap mitigation.)
- **No self-reported confidence number.** LLM confidence is uncalibrated. Confidence is grounded in
  observable signals: how many substantive disagreements there were, reversibility, and the density
  of "what would flip this" triggers.
- **Integrity gate.** A worker returning empty (a down proxy, a timeout) must not be silently
  synthesized as if it answered — worst when the dropped voice was the only outside vendor. The run
  reports "N/total responded", caps confidence, and flags if diversity collapsed to one lineage.
- **It's a skill, not a Python orchestrator.** The intelligent steps (framing decision, synthesis,
  adjudication) stay in the model session; only the mechanical parts (parallel calls with a timeout
  and an integrity check, a vendor-diversity preflight) are tiny scripts. This avoids re-implementing
  agent orchestration in fragile shell.

## Known-limits summary

1. The merge carries the orchestrator's lineage. Mitigated, not removed, by the cross-vendor review.
2. Shared blind spots on pure-judgment questions are uncatchable here. Your skepticism is the backstop.
3. Confidence is a grounded heuristic, not a probability.
4. Vendor tags are self-declared; the preflight catches honest mistakes, not deception.
