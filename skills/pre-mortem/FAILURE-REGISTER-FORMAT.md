# Failure Register Format

Output path: `docs/pre-mortem/<slug>.md`

The register is the **Anchor**: it preserves the failure-mode → mitigation →
doc-change chain as a readable artifact. The pre-mortem does **not** silently rewrite
upstream docs (that would be a Black Box — the driving modes would vanish, and nobody
could later reconstruct why the design grew a retry queue). Each mode is either
mitigated via an *approved* edit, or accepted with a logged reason. Nothing is dropped.

## Template

~~~markdown
---
slug: <slug>
status: in-progress
deferred: []
last_session: <ISO timestamp>
prereqs:
  - path: docs/tech-design/<slug>.md
    expected_status: complete
  - path: docs/issues/<slug>.md
    expected_status: complete
  - path: docs/requirements/<slug>.md
    expected_status: complete
lenses_covered: []
novel_mode_count: 0
mundane_mode_count: 0
plan_changed: false
---

# Pre-Mortem — <Title>

## Framing
> It is <N months> after launch. This project failed — badly. Not underperformed.
> Failed. The reasons below are why.

## Failure register

| ID | Lens | Failure mode | Sev | Lk | Source | Resolution |
|----|------|--------------|-----|----|--------|------------|
| PM-001 | operational | <one-line mode> | H | M | both | edit-rec → §<n> design |
| PM-002 | delivery | <one-line mode> | H | H | human | accepted: <reason> |
| PM-003 | outcome | <one-line mode> | M | L | claude | edit-rec → FR-007 |

- **Sev / Lk**: H / M / L (severity, likelihood).
- **Source**: `claude` (only Claude's blind draft raised it), `human` (only the
  user did), `both` (both lists). `claude` and `human` rows are the **novel modes**
  — the blind-draft gap. Count them into `novel_mode_count`.
- **Resolution**: either `edit-rec → <target>` (a proposed change to an upstream doc,
  applied only on user approval) or `accepted: <reason>`.

## Proposed edits (pending approval)

### PM-001 → docs/tech-design/<slug>.md §<n>
**Change:** <concrete edit text>
**Status:** proposed | applied <ISO timestamp> | rejected: <reason>

## Accepted risks

### PM-002
**Why accepted:** <reason the team is choosing to carry this risk>
**Trigger to revisit:** <what condition would force re-evaluation>

## Open questions

### OQ-001: <mode we can't score yet>
**What we know:** <facts>
**What would unblock:** <who to ask / what to measure>
**Affects:** <PM-IDs>
~~~

## Rules

- PM IDs are stable. Never renumber.
- Every mode in the register has a Resolution — an `edit-rec` or an `accepted`. A mode
  with no resolution is a Silent Fallback (a known risk dropped on the floor) and
  blocks completion.
- Every High×High and High×Medium mode must be resolved before `status: complete`.
- `edit-rec` rows do not modify the upstream doc until the user approves; on approval,
  apply the edit, stamp `applied <timestamp>`, and set frontmatter `plan_changed: true`.
- `accepted` rows require a reason and a revisit trigger — acceptance is a decision,
  not a shrug.
