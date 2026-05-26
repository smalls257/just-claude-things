# Frontmatter Format — Pre-Mortem Register Schema

Every `docs/pre-mortem/<slug>.md` starts with this YAML frontmatter block. It
extends the shared `*-grill` schema with pre-mortem success-proxy fields so the
NEG-AUDIT can check anti-theater signals without re-deriving them.

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
prereqs:                       # the docs this pre-mortem attacked — audit trail
  - path: docs/tech-design/<slug>.md
    expected_status: complete
  - path: docs/issues/<slug>.md
    expected_status: complete
  - path: docs/requirements/<slug>.md
    expected_status: complete
lenses_covered: [outcome, operational, delivery]   # required; all three before complete
novel_mode_count: <int>        # modes from the blind-draft gap (claude-only XOR human-only)
mundane_mode_count: <int>      # boring modes present; must be >= 2 before complete
plan_changed: true | false     # did any edit get applied to an upstream doc?
---
```

## Rules

- `slug` is the canonical kebab-case identifier shared across all docs for one feature.
- `status` flips to `complete` only when the neg-audit passes (`NEG-AUDIT.md`).
- `deferred[]` entries each have a stable `id`. Once assigned, never renumber. If a
  gap appears (D-001, D-003 — D-002 removed), preserve the gap. The original ID keeps
  the audit trail intact.
- `last_session` is auto-stamped every time the skill writes the file.
- `prereqs[]` records the three docs this pre-mortem read. It is the audit trail.
- `plan_changed` tracks *applied edits only*. An all-accepted run with no applied edits
  leaves it `false` and still passes — the NEG-AUDIT plan-change gate covers accepted
  risks separately. `plan_changed: false` on a complete register is not "the skill did
  nothing"; check the accepted-risks section.
- `novel_mode_count`, `mundane_mode_count`, `plan_changed` are the success proxies.
  They are facts derived from the register body, not aspirations. The NEG-AUDIT reads
  them; a `novel_mode_count: 0` or `plan_changed: false` run is **suspicious**, not
  passing — see `NEG-AUDIT.md`.

## D-XXX vs OQ-XXX

Two distinct entry types — do not conflate:

| Type | Where | Meaning | When to use |
|------|-------|---------|-------------|
| `D-XXX` | frontmatter `deferred[]` | A failure mode or mitigation explicitly deferred to a later session or downstream owner | Known mode, postponed decision |
| `OQ-XXX` | doc body **Open Questions** section | A failure mode whose severity/likelihood can't be judged without input | Unknown, needs clarification |

Use `D-XXX` when you know the mode but defer the mitigation. Use `OQ-XXX` when you
genuinely cannot score the mode yet.
