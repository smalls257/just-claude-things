# AGENTS.md Template (per module)

Used by `scaffold-with-guardrails` to generate one `AGENTS.md` per module.
Skill substitutes placeholders and populates the arch rules table (one row per rule).

## Template

```markdown
# {{MODULE_NAME}} — AGENTS.md

See root `CLAUDE.md` for global principles. This file covers
{{MODULE_NAME}}-specific rules.

## Purpose

{{MODULE_PURPOSE}}

## Principles at this Scale

- **Anchor** — {{ANCHOR_NOTE}}
- **Shield** — {{SHIELD_NOTE}}
- **Filter** — {{FILTER_NOTE}}
- **Buffer** — {{BUFFER_NOTE}}
- **Sensor** — {{SENSOR_NOTE}}
- **Engine** — {{ENGINE_NOTE}}

## What Belongs Here
- {{BELONGS_ITEMS}}

## What Does Not Belong Here
- {{NOT_BELONGS_ITEMS}}

## Naming Rules
- Capability-verb names from the domain
- Module-specific conventions: {{NAMING_NOTES}}

## Testing Rules

- Unit tests in `tests/{{APP_NAME}}.Tests.Unit/{{MODULE_NAME}}/`
- One test per public surface, happy + primary failure path minimum
- Stubs, not mocks. Real-shaped data from test doubles.

## Architectural Rules

| ID | Rule |
|----|------|
| `{{MODULE_KEY}}-R001` | {{RULE_1}} |
| `{{MODULE_KEY}}-R002` | {{RULE_2}} |

Each rule has:
- A matching `.semgrep/{{APP_LOWER}}/{{MODULE_LOWER}}.yaml` entry
- A matching NetArchTest test in
  `tests/{{APP_NAME}}.Tests.Unit/Architecture/{{MODULE_NAME}}ArchitectureTests.cs`

Track accepted violations as:
`[Fact(Skip = "{{MODULE_KEY}}-V001: <explanation>")]`
```

## Placeholders

| Placeholder | Source |
|-------------|--------|
| `{{MODULE_NAME}}` | Component name from tech design |
| `{{MODULE_KEY}}` | Uppercase short code, e.g., `DOMAIN` |
| `{{MODULE_LOWER}}` | Lowercase version, e.g., `domain` |
| `{{APP_NAME}}` | From grill answer |
| `{{APP_LOWER}}` | Derived |
| `{{MODULE_PURPOSE}}` | Component Responsibility from tech design |
| `{{ANCHOR_NOTE}}` through `{{ENGINE_NOTE}}` | Skill-generated per module context |
| `{{BELONGS_ITEMS}}` | From tech design Component "Owns" |
| `{{NOT_BELONGS_ITEMS}}` | Inferred from Responsibility matrix |
| `{{NAMING_NOTES}}` | Skill-generated |
| `{{RULE_1}}`, `{{RULE_2}}` | Skill-generated arch rules |
