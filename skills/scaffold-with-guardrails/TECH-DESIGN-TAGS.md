# Tech-Design XML Tag Schema

This document defines the XML tag schema embedded in tech-design docs at
`docs/tech-design/<slug>.md`. The `scaffold-with-guardrails` skill reads
these tags during Phase-2 (domain populate) to emit C# skeletons.

Tags are optional. A tech-design doc with no `<module>` tags will be
processed by Phase-1 only — Phase-2 is skipped.

## Outer wrapper

```xml
<module name="Orders">
  <entities>...</entities>
  <enums>...</enums>
  <contracts>...</contracts>
  <endpoints>...</endpoints>
</module>
```

### Rules

- `<module name="X">` required when tagging a module. `X` is PascalCase
  and becomes the folder name under `src/Domain/`, `src/Persistence/`,
  `src/Api/`, etc.
- Inner tags `<entities>`, `<enums>`, `<contracts>`, `<endpoints>` — any
  combination, all optional.
- Multiple `<module>` blocks per tech-design doc are allowed.
- `<module name="Shared">` is reserved for cross-cutting value objects
  (e.g., `Money`, `Address`). Other modules may reference Shared types
  freely. Modules MUST NOT reference each other directly.

## Inner format

`### H3` inside a tag = one item (entity / enum / contract / endpoint).

A fenced SQL block inside an `<entities>` H3 = the persistence schema for
that entity. Phase-2 uses it as the source for both the Dapper row type
and the migration SQL.

### Full example

````markdown
<module name="Orders">

<entities>

### Order

Represents a customer's purchase intent. Transitions through a single
approval workflow: pending → approved | denied.

```sql
CREATE TABLE orders (
  id           UUID        PRIMARY KEY,
  customer_id  UUID        NOT NULL,
  status       TEXT        NOT NULL CHECK (status IN ('pending','approved','denied')),
  total_cents  BIGINT      NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
```

**Invariants:** total_cents > 0; status transitions pending→approved|denied only.

</entities>

<enums>

### OrderStatus

- pending
- approved
- denied

</enums>

<contracts>

### CreateOrderRequest

- customerId: Guid — required
- items: LineItem[] — min 1

### OrderResponse

- id: Guid
- status: OrderStatus
- totalCents: long

</contracts>

<endpoints>

### POST /orders

- Request: CreateOrderRequest
- Response: 201 OrderResponse
- Auth: required

### GET /orders/{id}

- Response: 200 OrderResponse | 404

</endpoints>

</module>
````

## Cross-module reference rule

Entity fields use primitive types for foreign-key relationships across
modules. `Guid customerId` is allowed; `Customer customer` is not. Joins
happen in the Application layer, authored by devs.

Phase-2 pre-check fails loud on any cross-module entity reference. No
silent rewrite to primitives — the tech-design must spell it correctly.

## Validation

The Phase-2 pre-check enforces:

| Rule | Violation message |
|---|---|
| `<module name="X">` well-formed | "Malformed `<module>` tag at line N" |
| Each `<entities>` H3 has SQL fence | "Entity X missing SQL CREATE TABLE block" |
| `<endpoints>` Request/Response refs exist in `<contracts>` | "Endpoint X references undefined DTO Y" |
| Cross-module ref uses primitive | "Field X.Y references cross-module entity Z; use ID instead" |

## `<conventions>` block (Phase-1.5)

After `<module>` blocks, the convention scan writes one `<conventions>` block
capturing all adoption decisions:

```xml
<conventions
    reference-repo="../canonical-api"
    reference-repo-commit="a1b2c3d"
    scanned-at="2026-05-20T14:32:00Z"
    engine-version="0.1.0">

  <adopted
      detector="auth-jwt-bearer"
      source="src/Auth/JwtExtensions.cs:L12-L45"
      staged="staged/auth-jwt-bearer.cs"
      packages="Microsoft.AspNetCore.Authentication.JwtBearer:8.0.5"/>

  <rejected
      detector="caching-redis"
      source="src/Caching/RedisExtensions.cs:L8-L40"
      reason="dev-skipped"/>

  <dev-named
      target="feature-flags"
      source="src/Features/FlagExtensions.cs:L8-L30"
      staged="staged/dev-feature-flags.cs"
      adopted="true"
      packages="LaunchDarkly.ServerSdk:8.2.1"/>

  <discovered
      name="correlation-middleware"
      source="src/Mw/CorrelationMw.cs:L1-L60"
      staged="staged/discovered-correlation-middleware.cs"
      adopted="true"
      packages=""/>

  <conflict
      winner="auth-jwt-bearer"
      loser="httpclient-token-handler"
      overlap="src/Auth/JwtExtensions.cs:L50-L55"/>
</conventions>
```

**Field invariants:**
- `staged` paths are relative to `.scaffold/`
- `packages` is comma-separated `name:version` (Phase-2 cascade reads this)
- `reference-repo-commit` lets Phase-2 detect drift since scan
- `engine-version` lets future skill versions detect old block schemas
- `<rejected>` entries are kept (not deleted) so re-runs default to previous
  decision
