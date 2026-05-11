# Requirements Doc Format

Output path: `docs/requirements/<slug>.md`

## Template

The template below is what the skill produces. Write it as a code block so it's
copy-paste safe.

~~~markdown
---
slug: <slug>
status: in-progress
deferred: []
last_session: <ISO timestamp>
prereqs: []
---

# Requirements — <Title>

## Problem
<Why does this need to exist? Why now?>

## Users
- **Primary**: <who lives this hardest>
- **Secondary**: <who's adjacent>

## Scope
**In:**
- <bullet>

**Out:**
- <bullet>

## Functional requirements

### FR-001: <capability name>
<one paragraph: what the system does>

### FR-002: <capability name>
...

## Acceptance criteria

### FR-001
- [ ] <testable criterion>
- [ ] <testable criterion>

### FR-002
...

## Constraints
- <regulatory / org / integration / timeline — WHAT-level only, no tech>

## Open questions

### OQ-001: <one-line question>
**What we know:** <facts>
**What would unblock:** <who to ask / what to test>
**Affects:** <FR-IDs>

## Glossary
- **<Term>** — <definition in domain language>
~~~

## Rules

- FR IDs are stable. Never renumber.
- Every FR has at least one acceptance criterion.
- "Non-functional" terms (perf, security, scale) belong in tech design, not here.
- "Constraints" here means WHAT-level only — "must comply with HIPAA",
  not "use TLS 1.3".
- Glossary is lazy: only add terms users actually use or that need disambiguation.
  Promoted to root `CONTEXT.md` by `tech-design-grill`.
