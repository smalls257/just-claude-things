# Negentropic Self-Audit

Run this checklist before declaring `status: complete`. For each item, answer
YES (no violation) or NO (violation present) with one-line evidence. Any NO
without explicit user acknowledgment blocks completion.

## Violation Guide (from `~/.claude/CLAUDE.md`)

- [ ] **Paper Tiger** — Output meets stated need, not just stated spec. Evidence:
- [ ] **Distributed Monolith** — Units in output are atomically replaceable. Evidence:
- [ ] **Leaky Narrative** — No implementation detail bleeds through business interfaces. Evidence:
- [ ] **Infected Core** — Domain logic is not entangled with infrastructure. Evidence:
- [ ] **Black Box** — Failures and state are observable from outside. Evidence:
- [ ] **Computational Friction** — Scale and behavior come from thinking, not hardware/wasted ceremony. Evidence:
- [ ] **Forensic Coding** — The *why* is visible; readers don't reverse-engineer intent. Evidence:
- [ ] **God Class / Method** — No unit knows too much or does too much. Evidence:
- [ ] **Fossil Comments** — No comments describing absent or different behavior. Evidence:
- [ ] **Silent Fallback** — No swallowed failures returning fake success. Evidence:

## Closing the audit

If every box is YES, set `status: complete` in frontmatter and stop.

If any box is NO, do one of:
1. Fix the violation, re-run the audit.
2. Open an `OQ-XXX` / `D-XXX` entry with rationale and tell the user you cannot
   close the audit without acknowledgment. Set `status: in-progress`.
3. Stop the skill and ask the user to confirm the violation is intentional. If
   confirmed, record the acknowledgment in the doc with rationale.
