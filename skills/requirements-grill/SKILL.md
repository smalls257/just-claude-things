---
name: requirements-grill
description: Use when stress-testing or eliciting pure functional requirements for a product or feature. Drives the *what*, not the *how*. Refuses to discuss tech stack, architecture, or non-functional requirements. Triggers include "grill requirements", "what should this do", "define the what", "elicit requirements", "PRD interview".
---

<what-to-do>

Interview the user relentlessly about every functional requirement until shared understanding is reached. Walk the template in `REQUIREMENTS-FORMAT.md` section by section: Problem → Glossary.

Ask one question at a time. Provide your recommended answer with each question. Wait for feedback before continuing.

Pure *what*. Refuse tech-stack, architecture, or NFR detours — redirect to `tech-design-grill`.

Capture answers inline in `docs/requirements/<slug>.md` as each section closes. Do not batch.

For genuine unknowns, log `OQ-XXX`. For vague terms, propose canonical replacement and add to Glossary.

</what-to-do>

<supporting-info>

## Inputs

- **Prereqs:** none (head of pipeline).
- **Auto-scan at start (silent):** existing `CONTEXT.md`, prior `docs/requirements/`, recent commits. See `PREREQ-CHECK.md`.
- **External context (any time):** user may paste epics, PRDs, or prior docs mid-session. Accept and integrate.

## Output

`docs/requirements/<slug>.md` — see `REQUIREMENTS-FORMAT.md`.

## Boot sequence

1. Run startup logic from `PREREQ-CHECK.md`. If output file already exists in WIP state, offer to resume from `deferred[]`.
2. Announce to user:
   > *"This skill scans the repo for existing docs at start. You may paste epics or prior context any time. We're after the **what**, not the **how** — tech design happens later."*

## During the session

### One question at a time

Per `GRILL-LOOP.md`. Recommended answer included with every question. No vague deferrals — use `OQ-XXX` for genuine unknowns.

### Conflict with CONTEXT.md

Surface immediately. Do not paper over.

### Vague term

Propose canonical replacement. Glossary owns the language.

### Capture inline

Update `docs/requirements/<slug>.md` after each section is resolved. Do not batch.

## Completion gate

When every section has content and every conversation branch is closed (resolved or `OQ-ID`ed), run `NEG-AUDIT.md`. Pay particular attention to:

- **Paper Tiger** — Are FRs solving the stated need, or just the stated spec?
- **Forensic Coding** — Is the *why* visible in Problem and per-FR text?
- **Fossil Comments** — Have prior-session terms drifted from current intent?

Flip `status: complete` only if neg-audit passes. Otherwise stay in-progress and surface what's blocking.

## Hard rule

Do **not** discuss tech stack, architecture, components, frameworks, databases, or any infrastructure topic. If the user steers there, redirect:

> *"That's tech design — `tech-design-grill` handles it. Right now we're nailing the **what**."*

This is the Filter principle. The *how* contaminates the *what* if you let it.

## References

- `REQUIREMENTS-FORMAT.md` — output template
- `GRILL-LOOP.md` — interrogation pattern
- `PREREQ-CHECK.md` — startup logic
- `FRONTMATTER-FORMAT.md` — YAML schema
- `NEG-AUDIT.md` — completion gate

</supporting-info>
