# Prereq Check — Startup Logic

Each skill runs this at invocation.

## Resolution

1. Read your own prereq list from the **Inputs** section of this skill's content
   (the skill you are currently running). Each prereq has:
   - `path` — relative to repo root (e.g., `docs/requirements/<slug>.md`)
   - `expected_status` — usually `complete`

2. The `<slug>` is provided by the user at invocation. If not provided, ask:
   > *"Slug for this session? (kebab-case, e.g., `payment-gateway`)"*

3. For each prereq:
   - If file missing: **stop**. Message:
     > *"This skill requires `<path>`. Run `<upstream-skill-name>` first."*
   - Read YAML frontmatter. If `status != expected_status`: **stop**. Message:
     > *"Prereq `<path>` is `status: <actual>`, expected `<expected>`. Finish
     > the upstream session before continuing."*

4. After all prereqs pass, check your own output file (`<your-output-path>`):
   - If file exists with `status: in-progress`:
     > *"Last session left deferred items. Resume from where we left off, or
     > start fresh with a new slug?"*
     - **If resume:** reload the deferred[] entries from frontmatter and restart
       grill from the first section that has a D-XXX or OQ-XXX entry still open.
     - **If new slug:** ask for a new slug and proceed as if file missing.
   - If file exists with `status: complete`:
     > *"Doc marked complete. Overwrite (re-grill) or pick new slug?"*
     - **If overwrite:** confirm once, then proceed as if file missing.
     - **If new slug:** ask for a new slug and proceed as if file missing.
   - If file missing: proceed to grill.

5. **Tag well-formedness (Phase-2 prep).** Runs only after steps 1–4 pass —
   no point validating tags on a tech-design that hasn't reached `status: complete`.
   If the tech-design doc contains any `<module ` substring:
   - Scan for balanced `<module>...</module>` pairs. If unbalanced, report
     the line of the unmatched opening tag (or `EOF` if no opener was found).
   - Scan inner blocks `<entities>`, `<enums>`, `<contracts>`, `<endpoints>`
     for balanced open/close. Report the line of the unmatched opening tag.
   - Verify `<module name="X">` attribute is PascalCase. Report the line
     containing the offending `<module name="...">`.
   - **Collect all well-formedness failures.** Do not stop on the first one
     — report them together so the user fixes them in one pass (same shape
     as the Phase-2 pre-check failure report).
   - If any failures collected: **stop**. Message:
     > *"Tech-design `<module>` tags are malformed:*
     > *  1. line N1: `<snippet>` — <what's wrong>*
     > *  2. line N2: `<snippet>` — <what's wrong>*
     > *  ...*
     > *See `skills/scaffold-with-guardrails/TECH-DESIGN-TAGS.md` for the schema. Fix tags or remove them, then re-run."*

   This gate runs during Phase-1 prereq validation. Semantic cross-reference
   validation runs inside Phase-2 pre-check — **and only if Phase-2 is
   invoked.** If the user declines the Phase-2 handoff, no semantic check
   ever runs against the `<module>` tags. The well-formedness pass here
   does not certify the tech-design's internal consistency.

## Canonical paths

| Artifact | Path pattern |
|----------|-------------|
| Requirements doc | `docs/requirements/<slug>.md` |
| Tech design doc | `docs/tech-design/<slug>.md` |
| Issues list | `docs/issues/<slug>.md` |
| ADRs | `docs/adr/NNNN-<slug>-<topic>.md` |
| Project glossary | `CONTEXT.md` (repo root) |

## What to scan even without prereqs

Regardless of prereq state, silently scan repo at start:
- `CONTEXT.md` at root (glossary)
- `docs/adr/*.md` (decision records)
- Recent commits (`git log --oneline -20`)
- Existing `AGENTS.md` files for tone/conventions

Do **not** announce findings unless they conflict with something the user says.
