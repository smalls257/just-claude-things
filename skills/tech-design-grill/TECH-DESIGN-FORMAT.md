# Tech Design Doc Format

Output path: `docs/tech-design/<slug>.md`

## Template

~~~markdown
---
slug: <slug>
status: in-progress
deferred: []
last_session: <ISO timestamp>
prereqs:
  - path: docs/requirements/<slug>.md
    expected_status: complete
---

# Tech Design — <Title>

## Architecture overview
<one paragraph + a mermaid component diagram>

## Context boundaries
**Inside the app:** <what we build>
**Outside the app:** <what we integrate with or rely on>

## Components
### <ComponentName>
- Responsibility: <one sentence>
- Owns: <data / decisions>
- Depends on: <other components>
- Exposes: <surface>

## Responsibility matrix
| Component | Owns | Reads from | Writes to |
|-----------|------|------------|-----------|

## Data model
<entities, relationships, persistence choice>

## API contracts
### <Component> public surface
<methods, payload shapes, errors>

## Integration points
| System | Direction | Protocol | Auth |
|--------|-----------|----------|------|

## Key flows
~~~mermaid
sequenceDiagram
...
~~~

## Supporting diagrams
~~~mermaid
...
~~~

## Tech stack
| Layer | Choice | Rationale |
|-------|--------|-----------|

## NFRs
| Concern | Target | How enforced |
|---------|--------|--------------|

## Constraints register
| ID | Constraint | Source | Impact |
|----|-----------|--------|--------|

## Risks & mitigations
| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|

## ADRs
- [ADR-0001](../adr/0001-<slug>.md) — <title>

## Operations
- **Deploy:** <how>
- **Monitor:** <metrics, logs, traces>
- **Scale:** <scaling axis, limits>
~~~

## Rules

- Every Component has a Responsibility-matrix row.
- Every FR-XXX from requirements is traced to at least one Component.
- ADRs are lazy — only when hard-to-reverse + surprising + real trade-off.
- Glossary from requirements doc gets promoted to root `CONTEXT.md`
  (lazy creation, see `CONTEXT-FORMAT.md`).
