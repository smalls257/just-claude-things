# Prereq Check — Startup Logic

The pre-mortem runs at the last planning gate. It refuses to start until the whole
plan exists: design complete, tickets sliced, requirements readable for the goal.

## Resolution

1. The `<slug>` is provided by the user at invocation. If not provided, ask:
   > *"Slug for this pre-mortem? (kebab-case, e.g., `payment-gateway`)"*

2. For each prereq below, in order:
   - If file missing: **stop**. Message names the upstream skill to run.
   - Read YAML frontmatter. If `status != expected_status`: **stop**.

   | Prereq | Path | Expected | If missing/in-progress, tell user to run |
   |--------|------|----------|------------------------------------------|
   | Tech design | `docs/tech-design/<slug>.md` | `complete` | `tech-design-grill` |
   | Issues list | `docs/issues/<slug>.md` | `complete` | `to-issues` |
   | Requirements | `docs/requirements/<slug>.md` | `complete` | `requirements-grill` |

   Stop message template:
   > *"Pre-mortem requires `<path>` at `status: complete` (found `<actual>` /
   > missing). Run `<upstream-skill>` first. Pre-mortem is the last planning gate —
   > the plan must be whole before we attack it."*

3. After all prereqs pass, check the output file (`docs/pre-mortem/<slug>.md`):
   - If it exists with `status: in-progress`:
     > *"Last pre-mortem left deferred items. Resume, or start fresh?"*
     Resume: reload `deferred[]` and continue from the first open D-XXX/OQ-XXX.
     Start fresh: ask for a new slug and proceed as if the file were missing.
   - If it exists with `status: complete`:
     > *"Pre-mortem already complete for this slug. Overwrite (re-run) or new slug?"*
     Overwrite: confirm once, then proceed as if missing.
   - If missing: proceed to the loop.

## Canonical paths

| Artifact | Path pattern |
|----------|-------------|
| Requirements doc | `docs/requirements/<slug>.md` |
| Tech design doc | `docs/tech-design/<slug>.md` |
| Issues list | `docs/issues/<slug>.md` |
| Pre-mortem register | `docs/pre-mortem/<slug>.md` |
| Claude blind draft (transient) | `docs/pre-mortem/.<slug>-claude-draft.md` |
| ADRs | `docs/adr/NNNN-<slug>-<topic>.md` |
| Project glossary | `CONTEXT.md` (repo root) |

## What to scan even before drafting

Silently scan at start:
- `CONTEXT.md` at root (glossary — to use the project's terms in failure modes)
- `docs/adr/*.md` (decisions whose reversal risk is a failure mode)
- Recent commits (`git log --oneline -20`)
- `AGENTS.md` files for tone/conventions

Do **not** announce findings unless they conflict with something the user says, or
unless they themselves surface a failure mode (then log it in the register).
