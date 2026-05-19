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

5. **Tag well-formedness (Phase-2 prep).** If the tech-design doc contains
   any `<module ` substring:
   - Scan for balanced `<module>...</module>` pairs.
   - Scan inner blocks `<entities>`, `<enums>`, `<contracts>`, `<endpoints>`
     for balanced open/close.
   - Verify `<module name="X">` attribute is PascalCase.
   - If any well-formedness check fails: **stop**. Message:
     > *"Tech-design has `<module>` tags but they are malformed at line N
     > (`<actual snippet>`). See `skills/scaffold-with-guardrails/TECH-DESIGN-TAGS.md`
     > for the schema. Fix tags or remove them, then re-run."*

   This gate runs during Phase-1 prereq validation. Deep cross-reference
   validation runs later, inside Phase-2 pre-check.

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
