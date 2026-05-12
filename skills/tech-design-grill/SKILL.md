---
name: tech-design-grill
description: Use when designing a system after requirements are settled. Drives architecture, components, data model, API contracts, NFRs, and ADRs out of the room. Requires a complete requirements doc. Triggers include "tech design", "design the system", "how should we build this", "architecture session".
---

<what-to-do>

Interview the user relentlessly about every tech-design decision until shared understanding is reached. Walk the template in `TECH-DESIGN-FORMAT.md` section by section.

Ask one question at a time. Provide your recommended answer with each question. Wait for feedback before continuing.

Pure *how*. Assumes *what* is settled in `docs/requirements/<slug>.md` with `status: complete` — refuse to start otherwise.

If the codebase can answer a question (brownfield), explore the code instead of asking.

Trace every `FR-XXX` to an owning component. Reject the design if any FR has no owner.

Capture answers inline in `docs/tech-design/<slug>.md` and `CONTEXT.md` as decisions crystallise. Do not batch.

Use `D-XXX` for explicit deferrals (logged in frontmatter `deferred[]`). Offer an ADR only when the decision is hard to reverse, surprising without context, and reflects a real trade-off.

</what-to-do>

<supporting-info>

## Inputs

- **Required prereq:** `docs/requirements/<slug>.md` with `status: complete`. If missing or in-progress, stop and tell the user to run `requirements-grill`.
- **Auto-scan at start (silent):** existing `CONTEXT.md`, `docs/adr/*.md`, codebase if brownfield. See `PREREQ-CHECK.md`.
- **External context (any time):** accept and integrate.

## Outputs

- `docs/tech-design/<slug>.md` — primary. See `TECH-DESIGN-FORMAT.md`.
- `docs/adr/NNNN-<slug>-<topic>.md` — lazy. See `ADR-FORMAT.md`.
- `CONTEXT.md` at repo root — lazy. See `CONTEXT-FORMAT.md`.

## Boot sequence

1. Run `PREREQ-CHECK.md`. Refuse to start without a complete requirements doc.
2. **Promote glossary.** Read `Glossary` section of requirements doc. Offer to seed `CONTEXT.md` from it on first run.
3. **Trace requirements.** Read every `FR-XXX`. Build internal map: which component will own each FR. Reject the design if any FR has no owner.

## During the session

### One question at a time

Per `GRILL-LOOP.md`. Recommended answer included with every question.

### Explore code instead of asking

Brownfield: if a question can be answered by reading the codebase, read the codebase.

### Defer cleanly

`D-XXX` for explicit deferrals — log in frontmatter `deferred[]`. `OQ-XXX` from requirements either resolves here or stays open (carried forward).

### Offer ADRs sparingly

Only when **all three** hold:
- Hard to reverse
- Surprising without context
- Reflects a real trade-off (not just the obvious answer)

### Capture inline

Update the design doc + `CONTEXT.md` after each section. Do not batch.

## Completion gate

Run `NEG-AUDIT.md`. Focus:

- **Leaky Narrative** — Are component interfaces in domain language or tech?
- **Infected Core** — Does domain depend on infra anywhere?
- **God Class** — Any component owning too much?
- **Distributed Monolith** — Can components actually deploy / change independently?

Flip `status: complete` only if neg-audit passes.

## Hard rule

Do **not** open functional-requirement questions. If gaps surface, stop the session and tell the user to revisit `requirements-grill`. Don't paper over.

## References

- `TECH-DESIGN-FORMAT.md`
- `ADR-FORMAT.md`
- `CONTEXT-FORMAT.md`
- `GRILL-LOOP.md`
- `PREREQ-CHECK.md`
- `FRONTMATTER-FORMAT.md`
- `NEG-AUDIT.md`

</supporting-info>
