---
name: pre-mortem
description: Use as the last planning gate before scaffolding — stress-tests a completed plan (requirements + tech-design + tickets) for failure modes via a blind dual-draft pre-mortem, then emits a failure register with mitigations or accepted risks. Requires complete tech-design and issues docs. Triggers include "pre-mortem", "premortem", "how could this fail", "what could go wrong", "stress-test the plan", "risk the plan before we build".
---

<what-to-do>

Run a Klein-style pre-mortem on a completed plan, before any resource is committed to
building it. Assume the project has already failed badly; work backward to find why.

The defining mechanic is the **blind dual-draft** in `PREMORTEM-LOOP.md`: Claude
writes its own failure list to a sealed file *before* asking the user anything, the
user brain-dumps theirs freeform, and the user reveals first. This protects the
independence that makes a pre-mortem work — voicing a mode first anchors the other
party and collapses dissent (a social Silent Fallback). Do not short-circuit it.

Capture every mode in `docs/pre-mortem/<slug>.md` as it surfaces. Each mode ends as a
proposed upstream edit (applied only on approval) or an explicitly accepted risk. The
register never silently rewrites the design — it preserves the mode → mitigation chain.

</what-to-do>

<supporting-info>

## Inputs

- **Required prereqs (refuse to start otherwise):**
  - `docs/tech-design/<slug>.md` at `status: complete` — Operational lens.
  - `docs/issues/<slug>.md` at `status: complete` — Delivery lens.
  - `docs/requirements/<slug>.md` at `status: complete` — Outcome lens (goal/metric).
  See `PREREQ-CHECK.md`. If any is missing or in-progress, stop and name the upstream
  skill (`tech-design-grill`, `to-issues`, or `requirements-grill`).
- **Auto-scan at start (silent):** `CONTEXT.md`, `docs/adr/*.md`, recent commits,
  `AGENTS.md`. See `PREREQ-CHECK.md`.
- **External context (any time):** accept and integrate as failure modes.

## Outputs

- `docs/pre-mortem/<slug>.md` — the failure register. See `FAILURE-REGISTER-FORMAT.md`.
- Approved edits to upstream docs (requirements/tech-design/issues), applied only with
  user say-so and traced back to a PM-ID.

## Position in the pipeline

`requirements-grill → tech-design-grill → to-issues → [pre-mortem] → scaffold-with-guardrails`

Pre-mortem is the **last planning gate**, not the last step. The plan must be whole
but execution must not have started — scaffolding commits resources. Running the
pre-mortem after scaffold would be a Paper Tiger: it would emit a risk doc after
lock-in, unable to prevent the failure it exists to prevent.

## Boot sequence

1. Run `PREREQ-CHECK.md`. Refuse to start without all three complete docs.
2. Read the three docs. Use the project's glossary terms (`CONTEXT.md`) for failure
   modes so they land in domain language.

## During the session

Follow `PREMORTEM-LOOP.md` exactly, in order: frame → blind dual-draft (Claude commits
first, silently) → human reveals first → merge + dedupe → lens gap-check → score →
resolve → clean up the seal. Run `LENS-CHECK.md` for coverage *after* generation,
never before — running it first would anchor the user.

Capture inline. Update the register after each phase. Do not batch.

## Completion gate

Run `NEG-AUDIT.md`. Beyond the standard violation guide, the anti-theater gates are
hard:
- **Novel-mode gate** — `novel_mode_count >= 1`; a zero gap is suspicious, not passing.
- **Plan-change gate** — `plan_changed` is true or ≥1 risk is explicitly accepted; a
  no-change run must be justified, not auto-passed.
- **Mundane coverage** — `mundane_mode_count >= 2`.
- **Lens coverage** — all three lenses represented.

Flip `status: complete` only if the neg-audit passes.

## Hard rules

- **Do not voice a failure mode before the user's freeform dump is on the board.** The
  blind draft stays sealed until then. This is the whole technique.
- **Do not rewrite upstream docs silently.** Every applied edit is approved and traced
  to a PM-ID.
- **Do not pass a frictionless run.** Zero novel modes or zero plan change is a finding
  to justify, not a green light.

## References

- `PREMORTEM-LOOP.md`
- `LENS-CHECK.md`
- `FAILURE-REGISTER-FORMAT.md`
- `PREREQ-CHECK.md`
- `FRONTMATTER-FORMAT.md`
- `NEG-AUDIT.md`

</supporting-info>
