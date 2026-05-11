# Issue List Format

Output path: `docs/issues/<slug>.md`

## Template

~~~markdown
---
slug: <slug>
status: complete
source_requirements: docs/requirements/<slug>.md
source_tech_design: docs/tech-design/<slug>.md
generated: <ISO date>
---

# Issues — <Title>

## Dependency graph

~~~mermaid
graph TD
    ISSUE-001 --> ISSUE-002
    ISSUE-001 --> ISSUE-003
    ISSUE-002 --> ISSUE-004
~~~

## Foundation
(Scaffold tasks or one-time setup not covered by the scaffold skill)

### ISSUE-001: <foundation capability>
...

## Vertical slices
(Tracer-bullet features, topological order — deps appear before dependents)

### ISSUE-N: <capability name>
...

## Spikes
(One per OQ-XXX from requirements, one per D-XXX deferred from tech design)

### ISSUE-M: spike — resolve OQ-001 (<one-line description>)
...
~~~

## Per-issue format

~~~markdown
### ISSUE-NNN: <capability-name>
**Slice:** <end-to-end behavior delivered>
**Depends on:** ISSUE-XXX, ISSUE-YYY (or `none`)
**Touches:** <components from tech design>

#### Acceptance criteria
- [ ] <testable criterion>

#### Out of scope
- <deliberately deferred>

#### Source
- FR-XXX (requirements)
- §<section> (tech design)
- OQ-XXX or D-XXX (if a spike)
~~~

## Rules

- IDs are stable. Never renumber.
- Every FR-XXX from requirements is traced to ≥ 1 issue (validator enforces).
- Every OQ-XXX and D-XXX has a matching spike (validator enforces).
- Dependency graph must be acyclic (validator enforces).
- Issues listed in topological order (deps appear before dependents in the file).
