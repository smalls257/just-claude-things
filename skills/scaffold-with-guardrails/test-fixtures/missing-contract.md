---
status: complete
slug: missing-contract-demo
---

# Missing Contract — Tech Design

## Tech stack
- C# / .NET 9

## Architecture overview

Intentionally invalid fixture. CreateOrderRequest references a `LineItem` DTO that is not declared in `<contracts>` — Phase-2 pre-check P3 Rule 1 must flag this.

<module name="Orders">

<entities>

### Order

```sql
CREATE TABLE orders (
  id           UUID        PRIMARY KEY,
  total_cents  BIGINT      NOT NULL
);
```

</entities>

<contracts>

### CreateOrderRequest

- items: LineItem[] — required, min 1

</contracts>

<endpoints>

### POST /orders

- Request: CreateOrderRequest
- Response: 201

</endpoints>

</module>

<!-- LineItem DTO intentionally omitted. Pre-check must flag the undefined ref. -->
