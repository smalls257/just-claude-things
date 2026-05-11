---
name: tech-design-grill
description: Use when designing a system after requirements are settled. Drives architecture, components, data model, API contracts, NFRs, and ADRs out of the room. Requires a complete requirements doc. Triggers include "tech design", "design the system", "how should we build this", "architecture session".
---

# tech-design-grill

## Purpose

Drive complete tech design. Pure *how*. Assumes *what* is settled in
`docs/requirements/<slug>.md`.

## Inputs

- **Required prereq:** `docs/requirements/<slug>.md` with `status: complete`.
  If missing or in-progress, stop and tell the user to run `requirements-grill`.
- **Auto-scan at start (silent):** existing `CONTEXT.md`, `docs/adr/*.md`,
  codebase if brownfield. See `PREREQ-CHECK.md`.
- **External context (any time):** accept and integrate.

## Outputs

- `docs/tech-design/<slug>.md` — primary. See `TECH-DESIGN-FORMAT.md`.
- `docs/adr/NNNN-<slug>-<topic>.md` — lazy. See `ADR-FORMAT.md`.
- `CONTEXT.md` at repo root — lazy. See `CONTEXT-FORMAT.md`.

## Process

1. **Boot.** Run `PREREQ-CHECK.md`. Refuse to start without requirements doc.
2. **Promote glossary.** Read `Glossary` section of requirements doc. Offer
   to seed `CONTEXT.md` from it on first run.
3. **Trace requirements.** Read every FR-XXX. Build internal map: which component
   will own each FR. Reject the design if any FR has no owner.
4. **Grill, section by section.** Walk the template in `TECH-DESIGN-FORMAT.md`.
   Per `GRILL-LOOP.md`:
   - Recommended answer per question.
   - `D-XXX` for explicit deferrals — entry in frontmatter `deferred[]`.
   - OQ-XXX from requirements either resolve here or stay open (carried forward).
   - Offer an ADR only when *hard to reverse + surprising + real trade-off*.
5. **Capture as you go.** Update the design doc + `CONTEXT.md` inline.
6. **Completion gate.** Run `NEG-AUDIT.md`. Focus:
   - **Leaky Narrative** — Are component interfaces in domain language or tech?
   - **Infected Core** — Does domain depend on infra anywhere?
   - **God Class** — Any component owning too much?
   - **Distributed Monolith** — Can components actually deploy / change independently?
7. **Close.** Flip `status: complete` only if neg-audit passes.

## Hard rule

Do **not** open functional-requirement questions. If gaps surface, stop the
session and tell the user to revisit `requirements-grill`. Don't paper over.

## References

- `TECH-DESIGN-FORMAT.md`
- `ADR-FORMAT.md`
- `CONTEXT-FORMAT.md`
- `GRILL-LOOP.md`
- `PREREQ-CHECK.md`
- `FRONTMATTER-FORMAT.md`
- `NEG-AUDIT.md`
