# ADR Format

Output path: `docs/adr/NNNN-<slug>-<topic>.md`

NNNN is a 4-digit zero-padded counter, monotonically increasing per repo.

## When to create

All three must be true:
1. **Hard to reverse** — cost of changing later is meaningful.
2. **Surprising without context** — a future reader will wonder why.
3. **Real trade-off** — genuine alternatives existed and you picked one.

If any is missing, skip the ADR. Capture the reasoning in the tech design body
instead.

## Template

~~~markdown
# ADR-NNNN: <Title>

**Status:** proposed | accepted | superseded by ADR-MMMM
**Date:** <ISO date>
**Slug:** <slug>

## Context
<What forced this decision? Constraints in play.>

## Decision
<What we chose. One paragraph.>

## Alternatives considered
- **<Option A>** — why not.
- **<Option B>** — why not.

## Consequences
- **Positive:** <what becomes easier>
- **Negative:** <what becomes harder>
- **Reversibility cost:** <if we unwind this later, what does it cost?>
~~~
