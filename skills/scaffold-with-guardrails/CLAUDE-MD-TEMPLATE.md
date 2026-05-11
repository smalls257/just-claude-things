# CLAUDE.md Template (root)

Used by `scaffold-with-guardrails` to generate the repo-root `CLAUDE.md`.
Skill substitutes `{{PLACEHOLDERS}}` at scaffold time.

## Template

```markdown
# {{APP_NAME}} — Claude Code Standards

## Architecture

{{ARCHITECTURE_PARAGRAPH}}

**Stack:** {{STACK_SUMMARY}}

---

## Code Style

### Structure
- Top-down reading order: high-level entry points first, helpers below
- 15-line limit per function — extract a named helper if longer
- Max 3 levels of indentation
- One job per function

### Naming
- Business-domain verbs (not `HandleData`, `ProcessItem`, `DoThing`)
- Variables describe content + state (`matchingProjects`, `expiredGoals`)
- C#: PascalCase public, camelCase locals; Python: snake_case; don't mix

### Comments
- Forbidden: comments that describe what the code does
- Required: comments that explain *why* — business rules, constraints, trade-offs

---

## Complexity Guardrails
- Cyclomatic complexity < 15 per function
- Files > 200 lines are a warning sign — suggest decomposition
- No God Classes
- Interface before implementation (C#)

## Result Objects

Use `CSharpFunctionalExtensions` (Khorikov) `Result<T>` and `Result<T, TError>`.
Pattern-match at call sites; no exceptions for expected failures.

---

## Static Analysis

Semgrep runs before every build via `Directory.Build.targets`. Rules in
`.semgrep/{{APP_LOWER}}/`. Do not suppress findings. Do not use
`SKIP_SEMGREP=1` to bypass a violation.

Adding a rule: write YAML in `.semgrep/{{APP_LOWER}}/<layer>.yaml`. Add the
matching arch test in `tests/{{APP_NAME}}.Tests.Unit/Architecture/`. Verify
both fire before merging.

---

## Negentropic Lens

Every proposal, question, or request must include a violation analysis against
the Six Principles and Violation Guide (below). Lead with violation names
(bold), then one sentence of evidence. No preamble.

### The Premise

Software decays. Every change adds entropy. Our job is to inject order — to
make wanted change easy and unwanted change hard.

### The Yield

Readability, maintainability, testability, and scalability are **side effects**
of suppressed entropy. They are not goals. Never optimize for them directly.
Optimize for the principles below; the Yield follows.

### The Six Principles

1. **Anchor — Preservation of Intent.** Code carries the *why*. If the business
   reason is not visible in the code, the code is legacy the moment it's
   written.
2. **Shield — Structural Integrity.** Units are independent and atomically
   replaceable. Any node can be swapped, upgraded, or deleted without the
   system losing its identity.
3. **Filter — Narrative Abstraction.** Hide the *how* behind business-language
   interfaces. Call sites read as a story about the domain, not a tour of the
   implementation.
4. **Buffer — Subsidiarity.** Core logic never depends on specific
   infrastructure. Databases, queues, and APIs live at the periphery. The core
   passes the *Airplane Test*: it runs and reasons correctly with no network
   and no ceremony.
5. **Sensor — Decipherability.** You cannot stop decay you cannot see.
   Boundaries, side effects, and state are observable without a debugger and
   without redeployment.
6. **Engine — Mechanical Sympathy.** Computational waste is physical entropy.
   Respect the machine; algorithms before hardware.

### The Violation Guide

Name the failure when you see it. Named things can be fixed.

- **Paper Tiger** — Meets the spec, fails the need. Requirement-chasing instead
  of problem-solving.
- **Distributed Monolith** — Modules that cannot move independently. False
  seams; one change cascades everywhere.
- **Leaky Narrative** — Implementation detail bleeding through a business
  interface. The abstraction doesn't hold.
- **Infected Core** — Business rules entangled with their environment. Logic
  that cannot exist without its tools.
- **Black Box** — Failure is invisible from the outside. Debugging requires
  archaeology.
- **Computational Friction** — Scale achieved by adding hardware, never by
  thinking.
- **Forensic Coding** — Readers must reverse-engineer intent from ruins. The
  *why* is missing and has to be excavated.
- **God Class / God Method** — One unit knows too much and does too much. It
  cannot be tested, replaced, or reasoned about in isolation.
- **Fossil Comments** — Comments that describe code that no longer exists, no
  longer behaves that way, or never did. Lies preserved in amber.
- **Silent Fallback** — Code that swallows a failure and returns a fake
  success. A fallback that hides an error is worse than the error itself: the
  system appears healthy while broken. Visible errors are always preferable to
  invisible ones.

### The Mechanical Rules

Anchored on cognitive load. Humans track roughly seven things at once; code
that exceeds that fails silently in the reader's mind.

- **One function, one level of abstraction.** Don't mix orchestration with
  arithmetic.
- **A function fits in the reader's head.** If you cannot hold the whole
  function in mind while reading it, extract named helpers. The helper's name
  is documentation.
- **A file has one responsibility.** When a second responsibility appears,
  split the file. Size is a symptom, not the rule.
- **Nesting stays shallow.** Beyond a handful of levels, invert conditions,
  return early, or extract. Deep nesting is a cry for help.
- **Comments explain *why*, never *what*.** If the comment restates the code,
  rename the identifier or extract a function. Delete fossils on sight.
- **No new public surface without a test.** The test is the first caller and
  the first proof that the surface holds.
- **Capability-oriented names.** Functions, types, and files name the
  *capability* they provide, in the language of the domain. Not `handle`,
  `process`, `manage`, `do`.

### The Workflow Rules

1. **Plan before code.** Write what you're about to do and why before you open
   the editor.
2. **Flag existing violations before extending them.** Don't silently inherit
   rot. Name it, then decide whether to fix or work around it.
3. **Refactor before extend.** If the shape is wrong, fix the shape first,
   then add the feature. Never stack features on a broken abstraction.
4. **Read the local `AGENTS.md` before touching a subdirectory.**
5. **At every blocker, re-check the Six Principles and the Violation Guide.**
   A blocker is a signal — usually that the plan crosses a principle boundary
   or names a violation without realizing it.

### The Self-Audit

At the end of any response where you wrote code, walk the Violation Guide top
to bottom and ask: *did I just introduce any of these?* If yes, flag it
plainly before closing the turn. Silent violations are how entropy wins.

---

## This Codebase Specifically

{{CODEBASE_RULES}}
```

## Placeholders

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{{APP_NAME}}` | Grill answer | `ExpensePortal` |
| `{{APP_LOWER}}` | Derived from APP_NAME | `expense-portal` |
| `{{ARCHITECTURE_PARAGRAPH}}` | Tech design §Architecture overview | "Three-layer web application..." |
| `{{STACK_SUMMARY}}` | Tech design §Tech stack | "C# .NET 9 API + React + PostgreSQL" |
| `{{CODEBASE_RULES}}` | Skill-generated from Components + design principles | bullet list |
