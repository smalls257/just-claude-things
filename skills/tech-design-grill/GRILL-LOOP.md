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
8. **Cross-reference with what's known.** Check the user's current statement
   against, in order:
   (a) **the requirements doc** — every `FR-XXX` is settled fact. If a design
       choice contradicts an FR, surface it: *"FR-012 says cancellation is
       partial. Your proposed `Cancel(orderId)` endpoint can't express that."*
   (b) **this conversation** — earlier design decisions stay in force unless
       explicitly revisited. *"You said the saga owns refunds. Now you're
       putting refund logic in the order aggregate."*
   (c) **codebase, if it exists** — brownfield only. *"You said the new
       service owns inventory, but `InventoryService` already lives in the
       monolith. Are we extracting or duplicating?"*
   Resolution is one of: (i) latest intent wins → log prior as superseded
   or open `D-XXX` if reversal needs traceability; (ii) prior wins → correct
   the current statement; (iii) genuine open question → `OQ-XXX` (carries to
   later sessions) or `D-XXX` (deferred this session).

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
