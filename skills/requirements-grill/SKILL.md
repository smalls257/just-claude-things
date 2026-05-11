---
name: requirements-grill
description: Use when stress-testing or eliciting pure functional requirements for a product or feature. Drives the *what*, not the *how*. Refuses to discuss tech stack, architecture, or non-functional requirements. Triggers include "grill requirements", "what should this do", "define the what", "elicit requirements", "PRD interview".
---

# requirements-grill

## Purpose

Drive functional requirements out of the room. Pure *what*. No tech. No NFRs.
Audience-agnostic — works for solo, PO+eng, or any combination.

## Inputs

- **Optional prereqs:** none (this is the head of the pipeline)
- **Auto-scan at start (silent):** existing `CONTEXT.md`, prior
  `docs/requirements/`, recent commits. See `PREREQ-CHECK.md` for details.
- **External context (any time):** user may paste epics, PRDs, or prior docs
  mid-session. Accept and integrate.

## Output

`docs/requirements/<slug>.md` — see `REQUIREMENTS-FORMAT.md`.

## Process

1. **Boot.** Run startup logic from `PREREQ-CHECK.md`. If output file already
   exists in WIP state, offer to resume from `deferred[]`.
2. **Announce.** State to the user:
   > *"This skill scans the repo for existing docs at start. You may paste
   > epics or prior context any time. We're after the **what**, not the **how**
   > — tech design happens later."*
3. **Grill, section by section.** Walk the template in `REQUIREMENTS-FORMAT.md`
   from Problem → Glossary. Per `GRILL-LOOP.md`:
   - One question at a time, recommended answer included.
   - No vague deferrals. Use `OQ-XXX` for genuine unknowns.
   - Conflict with `CONTEXT.md` → surface immediately.
   - Vague term → propose canonical replacement.
4. **Capture as you go.** Update `docs/requirements/<slug>.md` after each
   section is resolved. Do not batch.
5. **Completion gate.** When every section has content and every conversation
   branch is closed (resolved or OQ-IDed), run `NEG-AUDIT.md`. Pay particular
   attention to:
   - **Paper Tiger** — Are FRs solving the stated need, or just the stated spec?
   - **Forensic Coding** — Is the *why* visible in Problem and per-FR text?
   - **Fossil Comments** — Have prior-session terms drifted from current intent?
6. **Close.** Flip `status: complete` only if neg-audit passes. Otherwise
   stay in-progress and surface what's blocking.

## Hard rule

Do **not** discuss tech stack, architecture, components, frameworks, databases,
or any infrastructure topic. If the user steers there, redirect:

> *"That's tech design — `tech-design-grill` handles it. Right now we're
> nailing the **what**."*

This is the Filter principle. The *how* contaminates the *what* if you let it.

## References

- `REQUIREMENTS-FORMAT.md` — output template
- `GRILL-LOOP.md` — interrogation pattern
- `PREREQ-CHECK.md` — startup logic
- `FRONTMATTER-FORMAT.md` — YAML schema
- `NEG-AUDIT.md` — completion gate
