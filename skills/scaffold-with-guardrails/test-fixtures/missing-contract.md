---
status: complete
slug: missing-contract-demo
---

# Missing Contract — Tech Design

## Tech stack
- C# / .NET 9

## Architecture overview

Intentionally invalid fixture. Endpoint `POST /orders/items` references a
`LineItem` DTO that is not declared in `<contracts>` — Phase-2 pre-check
Rule 1 (endpoint → DTO refs) must flag this.

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

- totalCents: long — required, > 0

### OrderResponse

- id: Guid
- totalCents: long

</contracts>

<endpoints>

### POST /orders

- Request: CreateOrderRequest
- Response: 201 OrderResponse

### POST /orders/items

- Request: LineItem
- Response: 201 OrderResponse

</endpoints>

</module>

<!-- LineItem DTO intentionally omitted from <contracts>. Pre-check Rule 1
     must flag: "Endpoint Orders.POST /orders/items references undefined DTO LineItem". -->
