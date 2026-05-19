## What

<!-- One-paragraph summary of the change. Aim for "why," not "what". -->

## Why

<!-- Link the business / technical reason. Cite an issue, an incident, or a design doc. -->

## Six Principles check

- [ ] **Anchor** — the *why* is visible in code (comments where non-obvious, descriptive names)
- [ ] **Shield** — units remain independently replaceable
- [ ] **Filter** — call sites read in domain language, not implementation tour
- [ ] **Buffer** — no new infrastructure dependency leaked into the core
- [ ] **Sensor** — failures observable without a debugger
- [ ] **Engine** — no obvious computational waste introduced

## Tests

- [ ] Unit tests added / updated
- [ ] Integration tests (if cross-boundary)
- [ ] Architecture test (if new layer / dependency rule)
- [ ] Mutation score not regressed (review nightly Stryker artifact for new code)

## Gates

- [ ] Pre-commit gates green locally (`Verified: yes` on every commit)
- [ ] No `Verified: no` commits without `unsafe-skip` label
- [ ] `gates-backstop` workflow passing

## Risk + rollback

<!-- Production-affecting? Migration? Feature flag? How to roll back? -->

## Reviewer focus

<!-- Steer the reviewer: which file is load-bearing? Which is generated? -->
