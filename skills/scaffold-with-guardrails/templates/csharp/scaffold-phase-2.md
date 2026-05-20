# Phase-2: Domain Populate

> Invoked from `scaffold.md` Phase-1 final step when `<module>` tags are
> present in the tech-design doc and the user accepts the Phase-2 prompt.
> Reads tagged sections, emits typed C# skeletons that compile and fail
> loud at runtime.
>
> See `../../TECH-DESIGN-TAGS.md` for the tag schema.

## Entry conditions

You only enter Phase-2 if all of the following are true:

1. Phase-1 (`scaffold.md`) completed successfully — solution builds, arch
   tests pass on empty scaffold.
2. The tech-design doc at `docs/tech-design/<slug>.md` contains at least
   one `<module name="...">` block.
3. `../../PREREQ-CHECK.md` tag well-formedness validation passed.
4. The user answered **Y** to the Phase-1 → Phase-2 handoff prompt.

The prose list above is the intent. The pre-flight gate below is the
**tripwire** — without it, a subagent can silently scope-narrow Phase-1
(skip `.semgrep/`, `AGENTS.md`, NetArchTest, hooks) and still enter
Phase-2, producing a code-only scaffold with no governance. That is the
Silent Fallback this skill exists to prevent.

## Pre-flight gate (mandatory — do not skip)

Before any pre-check, parsing, or generation work, run **every** check
below from the repo root. **Collect all failures** and emit a single
batched report. Abort on any failure.

### Tripwire 1: Phase-1 artifact inventory

Each path below must exist. For directories, "exist" means present and
non-empty.

| Path                                                                | What it proves                                                          |
|---------------------------------------------------------------------|-------------------------------------------------------------------------|
| `*.sln`                                                             | `dotnet new sln` ran                                                    |
| `global.json`                                                       | SDK pin emitted                                                         |
| `Directory.Build.props`                                             | TWAE / lockfile-mode / InvariantGlobalization wired                     |
| `Directory.Build.targets`                                           | semgrep gate wired into `BeforeTargets="Build"`                         |
| `Directory.Packages.props`                                          | central package management active                                       |
| `coverlet.runsettings`                                              | coverage threshold (70%) configured                                     |
| `.editorconfig`                                                     | shared IDE baseline                                                     |
| `CLAUDE.md`                                                         | Six Principles + Violation Guide embedded                               |
| `.semgrep/`                                                         | semgrep rule directory exists                                           |
| `.semgrep/*/security.yaml`                                          | cross-cutting security rules                                            |
| `.semgrep/*/quality.yaml`                                           | code-quality baseline                                                   |
| `.semgrep/*/async.yaml`                                             | async correctness rules                                                 |
| `.claude/settings.json`                                             | hook wiring                                                             |
| `.claude/hooks/pre-commit.sh`                                       | pre-commit gate                                                         |
| `.claude/hooks/pre-push.sh`                                         | pre-push gate                                                           |
| `.github/PULL_REQUEST_TEMPLATE.md`                                  | PR-template gate checklist                                              |
| `src/*/AGENTS.md` (≥ 1)                                             | at least one per-layer governance doc                                   |
| `src/*/AssemblyMarker.cs` (≥ 1)                                     | at least one NetArchTest assembly anchor                                |
| `tests/*.Tests.Unit/Architecture/*ArchitectureTests.cs` (≥ 1)       | at least one NetArchTest exists                                         |
| `BYPASS-POLICY.md`                                                  | gate-bypass discipline doc copied from `templates/common/`              |
| `BRANCH-PROTECTION.md`                                              | branch-protection requirements doc copied from `templates/common/`      |
| `.githooks/pre-commit`                                              | gate-system local pre-commit hook                                       |
| `.githooks/pre-push`                                                | gate-system local pre-push hook                                         |
| `.githooks/commit-msg`                                              | gate-system commit-msg hook (enforces `Verified:` trailer when needed)  |
| `scripts/bootstrap.sh`                                              | reproducible bootstrap (`./scripts/bootstrap.sh` from scaffold step)    |
| `.tools/manifest.toml`                                              | pinned tool versions for `tools-pin-check.yml`                          |
| `.semgrep/packs/csharp.yaml`                                        | OWASP / C# rules pack copied from `templates/common/`                   |
| `.semgrep/packs/owasp-top-ten.yaml`                                 | OWASP top-ten rules pack copied from `templates/common/`                |
| `.github/workflows/gates-backstop.yml.disabled`                     | server-side backstop workflow (shipped disabled per scaffold step)      |
| `.github/workflows/tools-pin-check.yml`                             | tool-pin drift workflow                                                 |
| `.github/workflows/stryker-nightly.yml`                             | nightly Stryker mutation-test workflow                                  |
| `.gates.toml`                                                       | gate config (thresholds, rule packs in play)                            |
| `.gitconfig.gates`                                                  | per-repo git config that activates `.githooks/`                         |
| `stryker-config.json`                                               | Stryker mutation-test config                                            |
| `NuGet.Config`                                                      | project-scoped feed override (`<clear/>` + nuget.org); prevents inherited Azure DevOps feed from wedging `dotnet tool install` with 401 (Silent Fallback the scaffold step exists to avoid) |
| `docs/rules-audit.md`                                               | rules-audit doc for the OWASP / gate-system layer                       |

Concrete shell forms an LLM follows literally:

```bash
# `test -f *.sln` is a Silent Fallback: shell expands the glob before `test` sees it, so
# zero matches leaves the literal `*.sln` (false-success-by-accident) and multiple matches
# pass extra args to `test -f` (syntax error). `ls` collapses all three cases honestly.
ls *.sln >/dev/null 2>&1                                                      || echo "MISSING: *.sln"
test -f Directory.Build.targets                                               || echo "MISSING: Directory.Build.targets"
test -d .semgrep && [ "$(find .semgrep -name '*.yaml' | wc -l)" -gt 0 ]       || echo "MISSING: .semgrep/*.yaml"
test -f .claude/settings.json                                                 || echo "MISSING: .claude/settings.json"
test -f .claude/hooks/pre-commit.sh                                           || echo "MISSING: .claude/hooks/pre-commit.sh"
[ "$(find src -maxdepth 2 -name 'AGENTS.md' | wc -l)" -gt 0 ]                 || echo "MISSING: src/*/AGENTS.md"
[ "$(find src -maxdepth 2 -name 'AssemblyMarker.cs' | wc -l)" -gt 0 ]         || echo "MISSING: src/*/AssemblyMarker.cs"
[ "$(find tests -path '*/Architecture/*ArchitectureTests.cs' | wc -l)" -gt 0 ]|| echo "MISSING: tests/*.Tests.Unit/Architecture/*ArchitectureTests.cs"

# Gate-system layer (Phase-1 "Gate system installation (always)" step in scaffold.md)
test -f BYPASS-POLICY.md                                                      || echo "MISSING: BYPASS-POLICY.md"
test -f BRANCH-PROTECTION.md                                                  || echo "MISSING: BRANCH-PROTECTION.md"
test -f .githooks/pre-commit                                                  || echo "MISSING: .githooks/pre-commit"
test -f .githooks/pre-push                                                    || echo "MISSING: .githooks/pre-push"
test -f .githooks/commit-msg                                                  || echo "MISSING: .githooks/commit-msg"
test -f scripts/bootstrap.sh                                                  || echo "MISSING: scripts/bootstrap.sh"
test -f .tools/manifest.toml                                                  || echo "MISSING: .tools/manifest.toml"
test -f .semgrep/packs/csharp.yaml                                            || echo "MISSING: .semgrep/packs/csharp.yaml"
test -f .semgrep/packs/owasp-top-ten.yaml                                     || echo "MISSING: .semgrep/packs/owasp-top-ten.yaml"
test -f .github/workflows/gates-backstop.yml.disabled                         || echo "MISSING: .github/workflows/gates-backstop.yml.disabled"
test -f .github/workflows/tools-pin-check.yml                                 || echo "MISSING: .github/workflows/tools-pin-check.yml"
test -f .github/workflows/stryker-nightly.yml                                 || echo "MISSING: .github/workflows/stryker-nightly.yml"
test -f .gates.toml                                                           || echo "MISSING: .gates.toml"
test -f .gitconfig.gates                                                      || echo "MISSING: .gitconfig.gates"
test -f stryker-config.json                                                   || echo "MISSING: stryker-config.json"
test -f NuGet.Config                                                          || echo "MISSING: NuGet.Config"
test -f docs/rules-audit.md                                                   || echo "MISSING: docs/rules-audit.md"
```

The gate-system rows are not decorative. `BYPASS-POLICY.md` and the PR
template reference the `Verified:` trailer enforced by
`.githooks/commit-msg` and the `gates-backstop.yml` workflow. If those
files are absent, the docs become Forensic Coding (instructions for
plumbing that does not exist) and the Phase-2 scaffold ships with a
broken governance story. This tripwire is the Sensor that prevents
that drift.

Run them all. Do not stop on first failure.

### Tripwire 2: Build is green

```bash
dotnet build
```

Must exit `0` with zero errors. Warnings are allowed (the gate
infrastructure may emit `NU1507` or similar from the dev's NuGet config).

### Tripwire 3: Architecture tests pass

```bash
dotnet test --filter "FullyQualifiedName~Architecture"
```

Must exit `0`. All matched tests must Pass (Skipped is fine — but at
least one test must execute, and zero may Fail).

### Batched failure report

If any tripwire fails, print exactly this shape and abort:

```
Phase-2 pre-flight FAILED. Phase-1 is incomplete or broken.

Missing artifacts:
  - <path>
  - <path>

Build/test failures:
  - <verbatim summary of dotnet build / dotnet test output>

Resolution:
  - Re-run scaffold-with-guardrails Phase-1 to completion, OR
  - Hand-author the missing artifacts before re-invoking Phase-2.

Phase-2 will NOT proceed. The skill's guarantees (semgrep gates,
NetArchTest, hooks, layered AGENTS.md guidance) depend on every artifact
in tripwire 1 being present. A code-only scaffold with no governance is
the failure mode this gate exists to prevent.
```

Then stop. No Phase-2 file generation, no pre-check, no parsing.

If **all three** tripwires pass, proceed to `## Process overview`.

## Process overview

```
1. Pre-check — parse all <module> blocks, validate cross-references
2. (If gaps) Gap report → user prompts: fix and re-run, or proceed with stubs
3. Per module, per artifact type, emit files
4. Emit single 0001_initial_schema.sql (path per output-folder rule)
5. Run dotnet build
6. Summary report
```

## Pre-check

Before generating any files, validate the tag graph end-to-end. Fail loud
on every problem. **No silent fixes.** Tag well-formedness (e.g., balanced
`<module>` tags, parseable attributes) was already enforced by
`../../PREREQ-CHECK.md` per entry condition 3; this section validates the
**semantic cross-references** between modules, entities, enums, contracts,
and endpoints.

### Step P1: Parse all `<module>` blocks

For each `<module name="X">` block in the tech-design doc:

1. Record module name `X`.
2. For each inner tag (`<entities>`, `<enums>`, `<contracts>`, `<endpoints>`):
   - List each `### H3` item.
   - For entities: extract the SQL fence content (the `CREATE TABLE ...`
     statement). If no SQL fence inside an entity H3 → record as a
     **structural failure** (collected and reported by Step P4 alongside
     cross-reference failures, so the user sees all problems at once).

3. For each entity, parse the SQL CREATE TABLE to determine:
   - Column names and types (UUID, BIGINT, TEXT, TIMESTAMPTZ, etc.)
   - PK column
   - Each `CHECK (col IN ('a','b','c'))` → links to an `<enums>` entry
   - Each `*_id UUID NOT NULL` → FK candidate (P3 determines whether it is same-module or cross-module)

4. Record contracts and endpoints by name.

### Step P2: Build the type table

Build a single global table:

| Module | Kind | Name | References |
|---|---|---|---|
| Orders | entity | Order | OrderStatus (enum), CustomerId (Guid, cross-module ID — OK) |
| Orders | enum | OrderStatus | (none) |
| Orders | contract | CreateOrderRequest | (none) |
| Orders | endpoint | POST /orders | CreateOrderRequest, OrderResponse |
| ... | ... | ... | ... |

Print this table to the user before proceeding.

### Step P3: Validate cross-references

Run each rule. Collect all failures before prompting:

1. **Endpoint → DTO refs.** For each `<endpoint>`, the Request and Response
   types must exist in some `<contracts>` block (same module or `Shared`).
   - Failure: `"Endpoint {Module}.{POST /path} references undefined DTO {Name}"`

2. **Entity column enum refs.** If an entity column has `CHECK (col IN
   ('a','b','c'))`, that enum must exist in `<enums>` of the same module
   **or in `<module name="Shared">`'s `<enums>`**.
   - Failure: `"Entity {Module}.{Entity}.{column} CHECK constraint references undefined enum {Name}"`

3. **Cross-module entity refs forbidden.** Two surfaces to scan:
   - **In `<contracts>` field lists:** any field typed as
     `{OtherModule}.{Entity}` or as `{Entity}` where `{Entity}` is defined
     in a different module's `<entities>` block.
   - **In `<entities>` prose (outside the SQL fence):** any sentence
     introducing a field of type `{Entity}` (rather than a Guid ID) where
     `{Entity}` lives in another module.
   - SQL columns themselves use SQL primitive types (`UUID`, `BIGINT`, …) —
     a `*_id UUID NOT NULL` column is the **correct** cross-module FK shape
     and is not a violation. Only fail if the C#-side artifact (contract
     field or entity prose) carries the entity-typed reference.
   - Failure: `"Entity {Module}.{Entity}.{field} references cross-module entity {OtherModule}.{Entity}. Use Guid {field}Id instead."`

4. **Module name PascalCase.** `<module name="orders">` (lowercase) fails.
   - Failure: `"Module name '{name}' must be PascalCase"`

### Step P4: Gap report + user prompt

If any **structural** failures (from P1) or **cross-reference** failures (from P3) collected:

```
Phase-2 pre-check found N issues:

  1. Endpoint Orders.POST /orders references undefined DTO LineItem
  2. Entity Orders.Order.customer references cross-module entity Customers.Customer. Use Guid customerId instead.
  ...

Fix the tech-design and re-run, or proceed and stub the missing pieces
with `object` placeholders? [fix/proceed]
```

- If user picks `fix` → abort Phase-2 cleanly, print `"Tech-design at {path} needs updates. Re-run scaffold when ready."`
- If user picks `proceed` → continue to generation with `object` placeholder for undefined DTO refs, `Guid` placeholder for cross-module FK leakage. **Log every substitution in the summary report.**

If no failures, continue to generation without a user prompt.

## Generation: entities + row types

**Documentation-only entities.** If the entity's SQL fence contains only SQL comments and no `CREATE TABLE` statement, treat the entity as documentation-only: emit **no** Domain class, **no** Row type, **no** test stub, **no** migration entry. Log the skip in the summary report's `Documentation-only entities:` section.

For each entity in each module's `<entities>` block, emit two files:
the Domain entity (business object) and the Persistence row type (Dapper
materializer target).

### Domain entity — `src/{{APP_NAME}}.Domain/{{MODULE}}/{{ENTITY}}.cs`

`{{ENTITY}}` = the H3 heading text inside `<entities>`, stripped of the `### ` prefix and any whitespace. Use verbatim as the C# class name and as `{{ITEM}}` in the file header. If the heading contains a parenthetical descriptor (e.g., `### Order (aggregate root)`), strip everything from the first `(` onward.

This same rule applies to enum/contract/endpoint heading text but is stated here because Task 5 is the first generation section to consume it. Task 6 will inherit the rule.

Map the SQL CREATE TABLE to a C# class:

| SQL type | C# type |
|---|---|
| `UUID` | `Guid` |
| `BIGINT` | `long` |
| `INTEGER` | `int` |
| `TEXT` (with CHECK IN) | the matching enum type |
| `TEXT` (plain) | `string` |
| `TIMESTAMPTZ` | `DateTimeOffset` |
| `TIMESTAMP` | `DateTime` |
| `BOOLEAN` | `bool` |
| `NUMERIC(p,s)` | `decimal` |
| Any other SQL type | `object` — log as a gap in the summary report; dev resolves |

Entity template:

```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><entities>{{ENTITY}}</entities></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace {{APP_NAME}}.Domain.{{MODULE}};

public sealed class {{ENTITY}}
{
    public {{TYPE}} {{PROPERTY}} { get; private set; }
    // ... one private-set property per SQL column ...

    private {{ENTITY}}() { } // Object-initializer use by Create. Dapper hydrates {{ENTITY}}Row, not the Domain entity.

    // TODO: invariants from tech-design — {{INVARIANTS_QUOTE}}
    public static {{ENTITY}} Create({{CREATE_PARAMS}})
        => throw new NotImplementedException("TODO: enforce {{ENTITY}} invariants");
}
```

`{{INVARIANTS_QUOTE}}` = the `**Invariants:**` paragraph from the entity's
H3, verbatim. If no invariants paragraph, write `"TODO: define invariants"`.

`{{CREATE_PARAMS}}` = all non-PK, non-default columns as constructor params
in `(Type name, Type name)` form, lowerCamelCase.

### Persistence row type — `src/{{APP_NAME}}.Persistence/{{MODULE}}/{{ENTITY}}Row.cs`

Mirror the SQL columns exactly. POCO with public init/get, no behavior:

```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><entities>{{ENTITY}}</entities></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace {{APP_NAME}}.Persistence.{{MODULE}};

internal sealed record {{ENTITY}}Row(
    {{TYPE}} {{PROPERTY}},
    // ... one positional param per SQL column ...
);
```

Notes:
- Dapper materializes the row type, not the Domain entity. A repository/mapper in Persistence converts Row → Domain (authored by devs).
- Row type is `internal` — never exposed past the Persistence layer.
- `string` for enum columns in the row type (raw DB value). Domain entity
  parses the enum.
- Order of columns matches SQL CREATE TABLE order.

### Worked example (Orders.Order)

For the `valid-single-module.md` fixture, this generates:

`src/OrdersDemo.Domain/Orders/Order.cs`:
```csharp
// Generated by scaffold Phase-2 from docs/tech-design/orders-demo.md
// Source: <module name="Orders"><entities>Order</entities></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace OrdersDemo.Domain.Orders;

public sealed class Order
{
    public Guid Id { get; private set; }
    public Guid CustomerId { get; private set; }
    public OrderStatus Status { get; private set; }
    public long TotalCents { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private Order() { } // Object-initializer use by Create. Dapper hydrates OrderRow, not the Domain entity.

    // TODO: invariants from tech-design — total_cents > 0; status transitions pending→approved|denied only.
    public static Order Create(Guid customerId, long totalCents)
        => throw new NotImplementedException("TODO: enforce Order invariants");
}
```

`src/OrdersDemo.Persistence/Orders/OrderRow.cs`:
```csharp
// Generated by scaffold Phase-2 from docs/tech-design/orders-demo.md
// Source: <module name="Orders"><entities>Order</entities></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace OrdersDemo.Persistence.Orders;

internal sealed record OrderRow(
    Guid Id,
    Guid CustomerId,
    string Status,
    long TotalCents,
    DateTimeOffset CreatedAt
);
```

## Generation: enums

For each entry in `<enums>`, emit `src/{{APP_NAME}}.Domain/{{MODULE}}/{{ENUM}}.cs`.

`{{ENUM}}` follows the same H3-resolution rule defined in the entities section: stripped H3 text, parenthetical descriptors removed.

Bullet list items map to PascalCase enum members:

Source:
```markdown
### OrderStatus
- pending
- approved
- denied
```

Output:
```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><enums>{{ENUM}}</enums></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace {{APP_NAME}}.Domain.{{MODULE}};

public enum {{ENUM}} { Pending, Approved, Denied }
```

Member naming: snake_case in source → PascalCase in C# (e.g., `in_progress` → `InProgress`).

**Row → Domain conversion:** the Persistence row type carries the raw `string` DB value for enum columns. The mapper that converts `{{ENTITY}}Row` to `{{ENTITY}}` uses `Enum.Parse<{{ENUM}}>(row.{{PROPERTY}}, ignoreCase: true)` — where `{{PROPERTY}}` is the PascalCase property name on the row type (the snake_case SQL column converted to PascalCase; e.g., `status` → `row.Status`). The mapper lives in Persistence (authored by devs); Phase-2 does not generate it.

## Generation: contracts (DTOs)

For each entry in `<contracts>`, emit
`src/{{APP_NAME}}.Api/{{MODULE}}/Contracts/{{DTO}}.cs`.

Source format (em-dash annotations per TECH-DESIGN-TAGS.md):
```markdown
### CreateOrderRequest
- customerId: Guid — required
- totalCents: long — required, > 0
```

Output:
```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><contracts>{{DTO}}</contracts></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace {{APP_NAME}}.Api.{{MODULE}}.Contracts;

public sealed record {{DTO}}(
    {{TYPE}} {{PROPERTY}},
    // ... one positional param per bullet ...
);
```

Notes:
- Em-dash annotations (`— required`, `— min 1`, `— > 0`) are stripped from generated code — they are human-author hints. **Not** rendered as validation attributes (out-of-scope).
- Collection types: `LineItem[]` → `IReadOnlyList<LineItem>`.
- If a bullet's type references an undefined DTO and the user picked `proceed` in pre-check, substitute `object` and log it in the summary report.

## Generation: route stubs

For each module with at least one `<endpoint>`, emit one file
`src/{{APP_NAME}}.Api/{{MODULE}}/{{MODULE}}Endpoints.cs` containing all
its endpoints.

Source format:
```markdown
### POST /orders
- Request: CreateOrderRequest
- Response: 201 OrderResponse
- Auth: required

### GET /orders/{id}
- Response: 200 OrderResponse | 404
```

Output:
```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><endpoints>...</endpoints></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
namespace {{APP_NAME}}.Api.{{MODULE}};

public static class {{MODULE}}Endpoints
{
    public static void Map{{MODULE}}Endpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/orders", IResult (CreateOrderRequest req)
            => throw new NotImplementedException("TODO: implement POST /orders"));
        app.MapGet("/orders/{id:guid}", IResult (Guid id)
            => throw new NotImplementedException("TODO: implement GET /orders/{id}"));
    }
}
```

Route signature rules:
- The path string in `app.Map{METHOD}("{PATH}", ...)` is the verbatim `{PATH}` from the H3 heading `### {METHOD} {PATH}`. Path params like `{id}` pass through unchanged.
- Path params like `{id}` become method params. Guid in path → `:guid` route constraint.
- Request body DTO appears as `(CreateOrderRequest req)` param.
- Response shape isn't typed at the route — it appears in the impl.
- **Explicit return type `IResult` is required on every lambda** (`IResult (CreateOrderRequest req) => throw …`). Without it, the throw-expression body collapses the lambda to `Func<T, Nothing>`, which the compiler then binds to the `MapPost(string, RequestDelegate)` overload (where the delegate signature is `(HttpContext) -> Task`) instead of the `(string, Delegate)` overload — producing `CS1661`/`CS1678` because `CreateOrderRequest` is not `HttpContext`. The `IResult` token gives the lambda a concrete return type, binds the `Delegate` overload, and compiles. **Required** — do not strip it.
- If the Request or Response type references an undefined DTO and the user picked `proceed` in pre-check, the route param type becomes `object` (e.g., `IResult (object req) => ...`). Log every such substitution in the summary report.
- Body is always `throw new NotImplementedException("TODO: implement {METHOD} {PATH}")`.

**Wiring into `Program.cs`:** Phase-2 does not modify `Program.cs`. Each module's `Map{{MODULE}}Endpoints` extension must be called explicitly — append `app.Map{{MODULE}}Endpoints();` to the endpoint-registration block in `Program.cs`. The Task 8 summary report lists every emitted endpoint extension as a wiring checklist so nothing is silently unreachable.

## Generation: test stubs

For each entity, emit
`tests/{{APP_NAME}}.Tests.Unit/{{MODULE}}/{{ENTITY}}Tests.cs`:

```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><entities>{{ENTITY}}</entities></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
using Xunit;

namespace {{APP_NAME}}.Tests.Unit.{{MODULE}};

public class {{ENTITY}}Tests
{
    [Fact(Skip = "TODO: write {{ENTITY}} tests")]
    public void Placeholder() { }
}
```

For each endpoint, emit
`tests/{{APP_NAME}}.Tests.Integration/{{MODULE}}/{{METHOD}}_{{PATH_SAFE}}_Tests.cs`:

`{{PATH_SAFE}}` is the path normalised for use as a C# identifier: `/` → `_`, `{x}` → `byX`, hyphens → `_`, dots → `_`, any `?...` query portion stripped. E.g., `/orders/{id}` → `orders_byId`; `/orders-export.csv` → `orders_export_csv`.

```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><endpoints>{{METHOD}} {{PATH}}</endpoints></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
using Xunit;

namespace {{APP_NAME}}.Tests.Integration.{{MODULE}};

public class {{METHOD}}_{{PATH_SAFE}}_Tests
{
    [Fact(Skip = "TODO: write {{METHOD}} {{PATH}} integration test")]
    public void Placeholder() { }
}
```

Notes:
- Stubs are `Skip`-marked so a fresh scaffold's `dotnet test` exits green. Devs remove the `Skip` attribute as they write each test — the skip message tells them what to write.

## Generation: migration SQL bootstrap

Emit a single file `0001_initial_schema.sql` (path determined by the
output-folder rule below) containing every SQL fence from every
module's `<entities>` block, concatenated in **document order**:
modules in the order their `<module name="…">` blocks appear in the
tech-design file, and within each module, entities in the order their
`### H3` items appear inside `<entities>`.

This file is **regenerated on every Phase-2 run.** It is intended as a
dev-environment bootstrap only — once schema lands in a deployed
environment, ongoing migrations are additive and dev-authored.

### File structure

```sql
-- Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
-- Regenerated on every Phase-2 run. Throwaway post-dev-deploy.
-- Source modules: Orders, Customers

-- ============================================================================
-- Module: Orders
-- ============================================================================

-- Source: <module name="Orders"><entities>Order</entities></module>
-- WARNING: forward FK reference — orders.customer_id REFERENCES customers (emitted in a later module).
CREATE TABLE orders (
  id           UUID PRIMARY KEY,
  customer_id  UUID NOT NULL REFERENCES customers(id),
  status       TEXT NOT NULL CHECK (status IN ('pending','approved','denied')),
  total_cents  BIGINT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- ============================================================================
-- Module: Customers
-- ============================================================================

-- Source: <module name="Customers"><entities>Customer</entities></module>
CREATE TABLE customers (
  id           UUID PRIMARY KEY,
  email        TEXT NOT NULL UNIQUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

(The Customers module appears second in the example to demonstrate the forward-FK warning — Orders references customers before customers is emitted.)

### Rules

- Module banner comment before each module's tables.
- Per-entity source comment naming the `<module>/<entity>` tag pair.
- Skip entities whose SQL fence contains only SQL comments (no `CREATE TABLE`). The summary report logs them under `Documentation-only entities:`.
- SQL fences copied **verbatim** — no rewriting, no normalization. The
  tech-design author controls the exact DDL.
- Output folder: if `db/migrations/` exists in the same directory as
  the Phase-1-emitted `.sln` file, use that path. Otherwise use
  `migrations/` in the `.sln` directory. The decision (which folder
  was chosen, and why) is logged in the Phase-2 summary report.
- FK CONSTRAINT clauses inside CREATE TABLE statements are preserved
  as-is. **Do not reorder** modules or entities to satisfy FK ordering —
  the tech-design author owns ordering by document position.
- For each `REFERENCES <table>` clause whose target table has not yet
  been emitted in the concatenation (i.e., a forward reference),
  **prepend an inline comment immediately above the offending
  statement** naming the source column and forward-target table:
  ```sql
  -- WARNING: forward FK reference — orders.customer_id REFERENCES customers (emitted in a later module).
  CREATE TABLE orders (
    ...
    customer_id UUID NOT NULL REFERENCES customers(id),
    ...
  );
  ```
  Detection is scoped to literal `REFERENCES <ident>` tokens inside the
  SQL fence — naming-convention FKs (`*_id UUID NOT NULL` with no
  `REFERENCES` clause) are **not** treated as cross-fence references
  here (Step P3 has already accepted them as primitives).
- Also mirror every forward-FK warning in the Phase-2 summary report
  (Task 8) as a "FK forward-reference" entry so devs see them in the
  one place they always read.

## Post-build validation

After all files are written, run `dotnet build` from the repo root.

```bash
dotnet build
```

Expected: BUILD SUCCEEDED.

If build fails:

1. **Do not delete or roll back generated files.** They stay on disk.
2. Print the compiler errors verbatim.
3. Add a section to the summary report:
   ```
   dotnet build FAILED with N errors:
     - {error 1}
     - {error 2}
   Files were written to disk. Inspect and fix manually.
   ```
4. Exit Phase-2 with non-zero status.

The most common causes are:
- A `<contract>` DTO uses a type not yet generated (e.g., `LineItem`)
  and pre-check skipped it. Add `<entities>LineItem</entities>` to the
  tech-design and re-run.
- Test project missing a `using Xunit;` (if Phase-1 scaffolded tests
  but the Xunit reference is in `Directory.Packages.props` only —
  unlikely but possible).
- Generated code clashes with hand-written code from a prior session.
  Inspect the **Files OVERWRITTEN** list in the summary report and
  `git diff` each entry against the prior commit, then merge by hand.
  Commit before re-running Phase-2 to prevent the next overwrite.

## Summary report

After successful build (or after failed-build report), print a summary:

Sections below labelled with `-- OR --` show alternative renderings — emit exactly one form per section based on the run's actual state.

```
=========================================
Phase-2 Domain Populate — Summary
=========================================

Tech-design: docs/tech-design/{{SLUG}}.md
Modules processed: Orders, Customers

Counts: {{N_ENTITIES}} entities, {{N_ENUMS}} enums, {{N_CONTRACTS}} contracts, {{N_ROUTES}} routes, {{N_FILES}} files written ({{N_OVERWRITTEN}} overwritten)

Migration output folder: migrations/   (or db/migrations/ if it existed)

Files generated (NEW):
  src/{{APP_NAME}}.Domain/Orders/Order.cs
  src/{{APP_NAME}}.Domain/Orders/OrderStatus.cs
  src/{{APP_NAME}}.Persistence/Orders/OrderRow.cs
  src/{{APP_NAME}}.Api/Orders/Contracts/CreateOrderRequest.cs
  src/{{APP_NAME}}.Api/Orders/Contracts/OrderResponse.cs
  src/{{APP_NAME}}.Api/Orders/OrdersEndpoints.cs
  tests/{{APP_NAME}}.Tests.Unit/Orders/OrderTests.cs
  tests/{{APP_NAME}}.Tests.Integration/Orders/POST_orders_Tests.cs
  tests/{{APP_NAME}}.Tests.Integration/Orders/GET_orders_byId_Tests.cs
  migrations/0001_initial_schema.sql

Documentation-only entities (skipped — comment-only SQL fence):
  (none)
  -- OR --
  Shared.Money

Files OVERWRITTEN (had prior contents):
  (none)
  -- OR --
  src/{{APP_NAME}}.Domain/Orders/Order.cs
  ... (lists files that existed)

Pre-check substitutions:
  (none)
  -- OR --
  Endpoint Orders.POST /orders Request: LineItem → object (user picked proceed)

FK forward-references in migration SQL:
  (none)
  -- OR --
  orders.customer_id REFERENCES customers (Customers module emitted after Orders)

Build status: SUCCEEDED
  -- OR --
Build status: FAILED — see errors above

Next steps:
  - Fill in `// TODO` blocks in Domain entities (invariants, factories)
  - Replace `throw new NotImplementedException()` in endpoint handlers
  - Replace `Placeholder()` test methods with real cases
  - Wire `app.MapOrdersEndpoints();` into Program.cs
  - Apply migration: `psql ... < migrations/0001_initial_schema.sql`
  - If any FK forward-references were reported above, verify table
    emission order satisfies your CREATE constraints before applying

=========================================
```

The summary is the last thing Phase-2 emits before exiting.

## File header template

Every generated `.cs` file MUST start with this header:

```csharp
// Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
// Source: <module name="{{MODULE}}"><{{TAG}}>{{ITEM}}</{{TAG}}></module>
// Devs: edit freely. Re-running Phase-2 overwrites. Commit before re-run.
```

The migration file uses a SQL-comment version:

```sql
-- Generated by scaffold Phase-2 from docs/tech-design/{{SLUG}}.md
-- Regenerated on every Phase-2 run. Throwaway post-dev-deploy.
```

Header placeholders are filled per-file by the generation prompts.
