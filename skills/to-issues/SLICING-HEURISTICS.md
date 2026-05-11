# Slicing Heuristics — Tracer-Bullet Vertical Slices

## What a good slice looks like

- **End-to-end.** Touches every layer it needs to deliver one demoable behavior.
- **Atomic.** Can be merged and shipped independently of other slices.
- **Demoable.** A reasonable user or stakeholder could see it work.
- **Small.** Fits in 1–3 days of work for one engineer.

## Anti-patterns to reject

- **Horizontal layer slice.** "Build all DB models." Not demoable, not shippable alone.
- **Cosmic slice.** "Implement the entire checkout flow." Too big — violates the 1–3 day rule.
- **Setup-only slice.** "Add logging infrastructure." Not a slice — fold into Foundation
  or the first slice that actually needs it.
- **Future-proofing slice.** "Add hooks for X we might want later." YAGNI. Skip it.

## How to slice from FRs

1. Read all FR-XXX from the requirements doc.
2. Group FRs that move together: same user goal, same component cluster, delivered together.
3. Order groups by dependency. The first slice should produce a thin end-to-end working
   version. Subsequent slices broaden + deepen.
4. Each group becomes one ISSUE. Acceptance criteria come directly from the FR's
   acceptance criteria.
5. Foundation items (one-time setup, scaffold tasks deferred from skill 3) come first.
   Spikes for OQ/D items go last.

## Tracer-bullet metaphor

The first slice fires from the gun → through every layer → to the target. One bullet.
It hits the target. Subsequent bullets are wider or louder, but the same trajectory
is proven by the first one. If your first slice doesn't fire end-to-end, the metaphor
breaks — reassess.

## Size sanity check

For each slice, ask: "Could one engineer do this in 1–3 days?" If no:
- Too big → split at the next natural FR boundary
- Too small → merge with an adjacent slice that shares the same user goal
