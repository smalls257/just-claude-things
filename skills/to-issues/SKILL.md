---
name: to-issues
description: Use when ready to break complete requirements + tech design into independently-shippable, tracker-agnostic issues. Outputs a markdown file using tracer-bullet vertical slices. Triggers include "break into tickets", "create issues", "slice the work", "issue list", "what should we build first".
---

# to-issues

## Purpose

Convert a complete requirements doc + complete tech design into a markdown
issue list. Tracer-bullet vertical slices. Tracker-agnostic — output is a
markdown file devs choose how to import.

## Inputs

- **Required prereqs:**
  - `docs/requirements/<slug>.md` with `status: complete`
  - `docs/tech-design/<slug>.md` with `status: complete`
  - If either is missing or not complete: stop. Tell the user which upstream
    skill to run.

## Output

`docs/issues/<slug>.md` — see `ISSUE-FORMAT.md`.

## Process

1. **Boot.** Run `PREREQ-CHECK.md`. Refuse if either prereq is missing or
   in-progress.
2. **Read both upstream docs.** Build internal maps:
   - All `FR-XXX` from requirements (need issue coverage)
   - All `OQ-XXX` from requirements (need spike issues)
   - All `D-XXX` from tech design frontmatter `deferred[]` (need spike issues)
   - All Components from tech design (slices touch them)
3. **Group FRs into slices** per `SLICING-HEURISTICS.md`. Each slice is
   end-to-end and demoable. Acceptance criteria come from the FR's criteria.
4. **Order slices topologically.** Cycles or horizontal slices fail the audit.
5. **Generate spike issues** — one per OQ-XXX, one per D-XXX.
6. **Write** `docs/issues/<slug>.md` per `ISSUE-FORMAT.md`. Include the
   mermaid dependency graph at top.
7. **Validate.** Run `python tools/validate-issues.py docs/issues/<slug>.md`
   from repo root. If it fails, fix and re-run. Do not declare complete until
   validator exits 0.
8. **Completion gate.** Run `NEG-AUDIT.md`. Focus:
   - **Distributed Monolith** — Are slices actually independently shippable?
   - **Paper Tiger** — Do acceptance criteria match the FR's acceptance criteria?
   - Coverage — Every FR/OQ/D has an issue?
9. **Close.** `status: complete` only if validator and neg-audit both pass.

## Grilling pattern

Most decisions are upstream. Skill grills only when:
- Slice ordering has ambiguity in the dependency graph
- A slice is over 1–3 days (needs splitting)
- OQ-XXX or D-XXX spike scope is unclear

## References

- `ISSUE-FORMAT.md`
- `SLICING-HEURISTICS.md`
- `tools/validate-issues.py`
- `GRILL-LOOP.md`, `PREREQ-CHECK.md`, `FRONTMATTER-FORMAT.md`, `NEG-AUDIT.md`
