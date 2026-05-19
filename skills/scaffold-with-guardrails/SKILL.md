---
name: scaffold-with-guardrails
description: Use when starting a new project after tech design is complete. Generates the repo scaffold (optionally populated from tech-design XML tags — Phase-2), root CLAUDE.md, per-module AGENTS.md with IDed architectural rules, matching semgrep rules, NetArchTest arch tests, and Claude-only git hooks. Triggers include "scaffold the repo", "set up the project", "wire in arch tests", "bootstrap new app".
---

# scaffold-with-guardrails

## Purpose

Convert a complete tech design into a living scaffold: code structure + governance
docs + machine-enforced architectural rules + Claude-only hooks.

## Inputs

- **Required prereq:** `docs/tech-design/<slug>.md` with `status: complete`.
  If missing or in-progress, stop and tell the user to run `tech-design-grill`.
- **Auto-scan at start (silent):** existing `CLAUDE.md`, `AGENTS.md`, `.semgrep/`.
  See `PREREQ-CHECK.md`.

## Outputs

- Directory structure per tech design Components + Responsibility matrix
- Root `CLAUDE.md` (from `CLAUDE-MD-TEMPLATE.md`)
- One `AGENTS.md` per module (from `AGENTS-MD-TEMPLATE.md`)
- One `.semgrep/<app-lower>/<module-lower>.yaml` per arch rule
- One NetArchTest test per arch rule in `tests/<App>.Tests.Unit/Architecture/`
- `Directory.Build.targets` — semgrep gate BeforeTargets="Build"
- `.claude/settings.json` + `.claude/hooks/{pre-commit,pre-push,stop-neg-audit}.sh`

### Phase-2 (opt-in, generated from tech-design XML tags)

- Domain entity classes, C# enums, Dapper row types, API DTO records
- Minimal route stubs and xUnit skip-stub tests
- `migrations/0001_initial_schema.sql` bootstrap

See `TECH-DESIGN-TAGS.md` for the tag schema.

## Process

1. **Boot.** Run `PREREQ-CHECK.md`. Refuse if no completed tech design.
2. **Detect stack** from tech design's Tech Stack section. C# / .NET 9 is
   first-class. Python and TypeScript have stub templates only — tell the user
   and ask whether to proceed as C# or pause.
3. **Grill briefly** (per `GRILL-LOOP.md`):
   - App name (PascalCase)
   - Which projects are needed: Api? Service? Client?
   - Client contracts: Domain types or pure DTOs?
4. **Prefer CLI scaffolders over hand-rolled files.** Run `dotnet new sln`,
   `dotnet new classlib`, etc. Follow `templates/csharp/scaffold.md` exactly.
   Never reproduce what a generator creates.
5. **Hand-write** only the files listed in `templates/csharp/scaffold.md`
   under "Files the skill hand-writes after dotnet new".
6. **For each Component in tech design:**
   - Generate `src/<App>.<Module>/AGENTS.md` from `AGENTS-MD-TEMPLATE.md`,
     substituting placeholders from the Responsibility-matrix row.
   - Generate at least 2-3 arch rules per module from `SEMGREP-RULE-COOKBOOK.md`.
     IDs: `<APP_KEY>-<MODULE_KEY>-R001` upward.
   - For each rule: write matching `.semgrep/` entry AND NetArchTest test.
     Both are required. Either alone is insufficient.
7. **Wire hooks.** Copy from `hooks/` to target `.claude/hooks/`. Write
   `.claude/settings.json`. Make scripts executable.
8. **Validate scaffold.**
   - Run `dotnet build` — semgrep gate must pass on empty scaffold.
   - Run `dotnet test --filter "FullyQualifiedName~Architecture"` — arch tests
     pass on empty scaffold.
9. **Completion gate.** Run `NEG-AUDIT.md`. Focus:
   - **Black Box** — every rule visible as test + semgrep entry?
   - **Silent Fallback** — no `catch (Exception) { return default }` patterns?
   - **Computational Friction** — used CLI scaffolders, not hand-rolled?
   - Every Component has matching dir + `AGENTS.md` + at least one arch rule?
10. **Close.** `status: complete` in the tech design doc only after scaffold
    validates AND neg-audit passes.
11. **Phase-2 handoff.** Detect `<module>` tags in the tech-design doc.
    If present, ask the user: *"Populate Domain/Persistence/API skeletons
    from the tagged sections? (Phase-2, opt-in)"*. On yes, follow
    `templates/csharp/scaffold-phase-2.md` exactly. On no or no tags,
    stop here. See the "Phase-1 → Phase-2 handoff" section of
    `templates/csharp/scaffold.md` for detection rules.

## Hard rules

- Do not silently produce a scaffold for a stack with only a stub template.
  Pause and ask the user.
- Do not hand-roll `.csproj`, `package.json`, `Cargo.toml`, etc. when a
  generator exists. That is **Computational Friction**.
- Every arch rule has **both** a semgrep rule AND an arch test. Dual encoding
  is non-negotiable — semgrep catches patterns at write time; arch tests catch
  them at build time. Different failure modes.

## References

- `CLAUDE-MD-TEMPLATE.md`
- `AGENTS-MD-TEMPLATE.md`
- `SEMGREP-RULE-COOKBOOK.md`
- `templates/csharp/scaffold.md`
- `templates/csharp/scaffold-phase-2.md`
- `TECH-DESIGN-TAGS.md`
- `hooks/pre-commit.sh`, `hooks/pre-push.sh`, `hooks/stop-neg-audit.sh`
- `GRILL-LOOP.md`, `PREREQ-CHECK.md`, `FRONTMATTER-FORMAT.md`, `NEG-AUDIT.md`

## Testing

bats-core is vendored as submodules under `tests/` (`_bats`, `_bats-support`,
`_bats-assert`). Run all tests with:

```
bats skills/scaffold-with-guardrails/tests/
```

Helpers live in `tests/bats-helpers/`:
- `fixtures.bash` — temp-repo setup (`new_repo`, `install_gates_template`, `cleanup_repo`).
- `assertions.bash` — gate-specific assertions (`assert_gate_blocked`, `assert_verified_trailer`).

New gate tests go in `tests/gates/*.bats`.
