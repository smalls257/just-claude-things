# CONTEXT.md Format

Path: `CONTEXT.md` at repo root.

## Purpose

Project domain glossary. Source of truth for terminology. Updated inline by
`tech-design-grill` as terms resolve. Other skills challenge user statements
against this file.

## Template

~~~markdown
# Project Context

> Domain glossary and shared mental model. Update when a term gets resolved or
> reframed.

## Glossary

### <Term>
**Definition:** <one paragraph in domain language>
**Not to be confused with:** <near-miss terms>
**Examples:** <one or two>

### <Term>
...

## Boundaries

**This project owns:** <bullet list>
**This project consumes:** <bullet list>
**This project does not concern itself with:** <bullet list>

## Conventions

- <Anything that affects how terms or types are named>
~~~

## Rules

- Only domain-meaningful terms. Not implementation details (no class names).
- Created lazily — only when first term is resolved.
- Capture as terms resolve. Don't batch.
- Never let the code and `CONTEXT.md` disagree silently — if you spot drift,
  surface it.
