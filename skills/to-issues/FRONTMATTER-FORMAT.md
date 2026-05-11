# Frontmatter Format — Shared YAML Schema

Every output doc produced by a `*-grill` or `to-issues` skill starts with this
YAML frontmatter block.

## Schema

```yaml
---
slug: <kebab-case>             # required
status: in-progress | complete # required
deferred:                      # optional list, may be []
  - id: D-001
    section: "§<n> <title>"
    reason: <why deferred>
    blocks: <downstream IDs if known, or "none">
last_session: <ISO 8601 timestamp>   # auto-updated by skill on save
prereqs:                       # optional list, may be []
  - path: docs/requirements/<slug>.md
    expected_status: complete
---
```

## Rules

- `slug` is the canonical kebab-case identifier shared across all docs for one feature.
- `status` flips to `complete` only when neg-audit passes (`NEG-AUDIT.md`).
- `deferred[]` entries each have a stable `id`. Once assigned, never renumber.
  If a gap appears (D-001, D-003 — D-002 removed), preserve the gap; do not
  renumber. The original ID keeps the audit trail intact.
- `last_session` is auto-stamped every time the skill writes the file.
- `prereqs[]` is what this skill needed to run. It is the audit trail.

## D-XXX vs OQ-XXX

Two distinct entry types — do not conflate:

| Type | Where | Meaning | When to use |
|------|-------|---------|-------------|
| `D-XXX` | frontmatter `deferred[]` | Scoped work or constraint explicitly deferred to a later session or downstream skill | Known answer, postponed decision |
| `OQ-XXX` | doc body **Open Questions** section | Unresolved ambiguity that requires input before the doc can be complete | Unknown answer, needs clarification |

Use `D-XXX` when you know what needs to happen but are deliberately deferring it.
Use `OQ-XXX` when you genuinely don't know the answer yet.

## Open Questions format (skill 1 body section)

`OQ-XXX` entries live in the **Open Questions** section of the requirements doc
body, not in frontmatter. Use stable IDs (never renumber). Example:

```markdown
### OQ-001: Who approves expense claims above £500?
**What we know:** Claims below £500 auto-approve. Above is unclear.
**What would unblock:** Confirm with finance team or check approval policy doc.
**Affects:** FR-003 (approval flow), FR-007 (notification)
```

Each OQ must eventually become either a resolved fact (remove the entry) or a
`D-XXX` deferred item (promote to frontmatter + carry into tech design).
