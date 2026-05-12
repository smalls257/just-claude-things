# Grill Loop — Interrogation Pattern

This is the shared interrogation pattern used by all `*-grill` skills.

## Rules

1. **One question at a time.** Wait for the answer before moving on.
2. **Provide your recommended answer with every question.** Format:
   > Question — *Recommended: <answer>. <one-line rationale>.*
3. **Prefer codebase exploration over asking.** If the answer is in code, find it.
4. **Reject vague deferrals.** "We'll figure that out later" is not an answer.
   Either resolve it, or open an `OQ-XXX` / `D-XXX` entry with rationale.
5. **Challenge against the glossary.** If a user term conflicts with `CONTEXT.md`,
   surface the conflict immediately: *"`CONTEXT.md` defines X as Y, but you seem
   to mean Z — which is it?"*
6. **Sharpen fuzzy language.** When a vague term appears, propose a canonical
   replacement: *"You're saying 'account' — Customer or User?"*
7. **Probe with concrete scenarios.** When relationships are stated abstractly,
   invent specific scenarios that force precision about boundaries. Pick edge
   cases, not happy paths — the boundary is where ambiguity lives.
   > *"A customer cancels an order with three line items, one already shipped.
   > What happens to the shipped line, the refund, and the order status?"*
   If the user answers in generalities, restate the scenario more concretely
   until the answer is unambiguous.
8. **Cross-reference with code.** Brownfield only. When the user states how
   something works, check whether the code agrees. If you find a contradiction,
   surface it immediately — do not paper over:
   > *"You said cancellation is partial, but `OrderService.Cancel` deletes the
   > whole order. Which is the source of truth — your intent, or the code?"*
   Resolution is one of: (a) intent wins, code is wrong → log as work; (b) code
   wins, intent was stale → update the doc; (c) both wrong → open `OQ-XXX`.

## Walking the decision tree

Resolve dependencies one branch at a time. Don't jump branches. When a branch
forks, resolve the fork before descending. Track resolved branches mentally so
you don't loop back.

## What counts as "answered"

- A statement of fact (preferred)
- An explicit `OQ-XXX` entry (skill 1) with rationale and what would unblock it
- An explicit `D-XXX` entry (skill 2) with rationale and what would unblock it

Nothing else.

## Completion signal

You may propose completion only when every branch the conversation opened has
been closed, every section in your output template has content, and the neg-audit
passes. See `NEG-AUDIT.md`.
