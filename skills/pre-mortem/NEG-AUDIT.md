# Negentropic Self-Audit

Run this before declaring `status: complete`. For each item answer YES (no violation)
or NO (violation) with one-line evidence. Any NO without explicit user acknowledgment
blocks completion.

## Violation Guide (from `~/.claude/CLAUDE.md`)

Four of the ten violations are omitted here: Computational Friction, God Class /
Method, Fossil Comments, and Infected Core target code and design artifacts, not a
prose risk register. The anti-theater gates below fill those slots. Do not re-add the
omitted four indiscriminately.

- [ ] **Paper Tiger** — The register surfaced modes the user did not already hold, and
  the plan changed or risks were explicitly accepted. A clean run that changed nothing
  fails this box. Evidence:
- [ ] **Silent Fallback** — Every mode has a resolution; no High×High or High×Medium
  mode is left unresolved or quietly dropped. Evidence:
- [ ] **Black Box** — Upstream docs were not silently rewritten; every applied edit is
  traceable to a PM-ID in the register. Evidence:
- [ ] **Distributed Monolith** — The Delivery lens checked whether slices can ship
  independently. Evidence:
- [ ] **Leaky Narrative** — Failure modes are stated in domain language, not as raw
  stack traces or implementation trivia. Evidence:
- [ ] **Forensic Coding** — The *why* of each accepted risk is recorded, not left for
  a future reader to reverse-engineer. Evidence:

## Anti-theater checks (pre-mortem specific)

A pre-mortem's whole reason to exist is to avoid being theater. These are hard gates:

- [ ] **Novel-mode gate** — `novel_mode_count >= 1`. Zero gap between the two blind
  drafts means anchoring leaked, the plan is trivial, or the draft was skipped. A zero
  here is **suspicious** — do not pass it without the user explicitly confirming the
  plan really is that well-understood. Evidence:
- [ ] **Plan-change gate** — `plan_changed == true` OR at least one `accepted` risk is
  logged with a reason. A run with zero applied edits *and* zero accepted risks is the
  Paper Tiger signature. The user must justify a no-change run, not have it pass
  silently. Evidence:
- [ ] **Mundane coverage** — `mundane_mode_count >= 2`. Evidence:
- [ ] **Lens coverage** — `lenses_covered` contains all three: outcome, operational,
  delivery (or a stated reason a lens is genuinely empty). Evidence:

## Closing the audit

If every box is YES, set `status: complete` and stop.

If any box is NO, do one of:
1. Fix the violation, re-run the audit.
2. Open a `D-XXX`/`OQ-XXX` with rationale and tell the user you cannot close without
   acknowledgment. Set `status: in-progress`.
3. Stop and ask the user to confirm the finding is intentional. If confirmed, record
   the acknowledgment in the doc with rationale. The novel-mode and plan-change gates
   in particular are designed to be *acknowledged*, not auto-passed.
