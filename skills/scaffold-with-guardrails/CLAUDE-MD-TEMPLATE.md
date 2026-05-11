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
the Six Principles and Violation Guide (from global CLAUDE.md). Lead with
violation names (bold), then one sentence of evidence. No preamble.

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
