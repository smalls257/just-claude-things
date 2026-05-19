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

If any condition fails, Phase-2 is skipped. Phase-1 already completed; the
scaffold is in a known-good state.

## Process overview

```
1. Pre-check — parse all <module> blocks, validate cross-references
2. (If gaps) Gap report → user prompts: fix and re-run, or proceed with stubs
3. Per module, per artifact type, emit files
4. Emit single migrations/0001_initial_schema.sql
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

## Generation: enums, DTOs, route stubs, tests

See section below — to be filled in Task 6.

## Generation: migration SQL bootstrap

See section below — to be filled in Task 7.

## Post-build validation + summary

See section below — to be filled in Task 8.

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
