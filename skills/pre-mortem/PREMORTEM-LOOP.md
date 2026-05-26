# Pre-Mortem Loop — Blind Dual-Draft Protocol

This replaces the elicitation `GRILL-LOOP` used by the other grills. A pre-mortem
cannot be pure elicitation: if Claude voices a failure mode first, it anchors the user
and the dissent the technique depends on collapses — a social **Silent Fallback**,
where the user's real concern gets swallowed and replaced with agreement to Claude's
framing, while the session *looks* done having surfaced nothing new. Independent
generation before sharing is the load-bearing property. Protect it.

## The protocol

### 1. Frame total failure
Tell the user, verbatim in spirit:
> *"It's <N months> after launch. This project failed — badly. Not underperformed.
> Failed. We're going to work backward and find every reason why."*
Pick `N` from the project's own horizon (first release + a usage cycle).

### 2. Blind dual-draft — Claude commits first, silently
Read all three prereq docs. Draft your own failure list across the lenses
(`LENS-CHECK.md`). **Write it to `docs/pre-mortem/.<slug>-claude-draft.md` and do
NOT show it, summarize it, or hint at its contents.** Then prompt the user:
> *"Before I share anything: spend a few minutes listing every way you think this
> fails. Freeform — don't organize, don't filter, don't worry about categories.
> I've written mine down already and sealed it; you won't see it until yours is on
> the board."*

The seal is procedural and real: your draft exists in the file before the user types
a word, so it cannot drift toward theirs, and theirs cannot be anchored by yours.

### 3. Human reveals first
Take the user's freeform dump onto the board **before** revealing your draft. Do not
react with your own modes yet. If the user dries up, prompt only with open nudges
("anything about the team? the data? the date?") — never with a specific mode from
your draft.

### 4. Merge + dedupe
Now reveal your draft. Merge the two lists. For each mode, mark Source:
- `both` — on both lists.
- `human` — only the user raised it.
- `claude` — only your draft raised it.
The `human`-only and `claude`-only modes are the **novel modes** — the blind-draft
gap, the ~30% the technique exists to surface. Call them out explicitly: *"You saw X
and I didn't; I saw Y and you didn't — these gaps are the point."* Count them into
`novel_mode_count`.

### 5. Lens gap-check + mundane sweep
Run `LENS-CHECK.md` against the merged list: is each lens represented? Are there
≥2 mundane modes? Generate to fill gaps now (after generation, never before).

### 6. Score
For each mode, ask the user for severity (H/M/L) and likelihood (H/M/L). Provide your
recommendation with each, one at a time:
> *"PM-004, data backfill corrupts historical rows — Recommended Sev H, Lk M:
> irreversible if undetected, but the migration is small. Agree?"*

### 7. Resolve
Walk modes worst-first (High×High down). For each, the user picks one:
- **Mitigate** — you propose a concrete edit to requirements/design/tickets, recorded
  as an `edit-rec` row. Apply it to the upstream doc **only on approval**; on approval
  stamp `applied` and set `plan_changed: true`.
- **Accept** — log an `accepted` row with reason + revisit trigger.
No third option. A mode left unresolved is a Silent Fallback and blocks completion.

### 8. Clean up the seal
Delete `docs/pre-mortem/.<slug>-claude-draft.md` once merged — it has served its
purpose and the merged register is the record of truth.

## What counts as "answered"
- A scored mode with a resolution (edit-rec or accepted).
- An explicit `D-XXX` deferral with rationale.
- An explicit `OQ-XXX` for a mode that genuinely can't be scored yet.
Nothing else. "We'll probably be fine" is not an answer — reframe it as an accepted
risk with a reason, or score it.

## Completion signal
Propose completion only when every mode is resolved, every lens covered, ≥2 mundane
modes present, and the neg-audit passes (`NEG-AUDIT.md`).
