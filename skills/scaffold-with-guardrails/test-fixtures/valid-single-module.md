---
status: complete
slug: orders-demo
---

# Orders Demo — Tech Design

## Tech stack
- C# / .NET 9
- PostgreSQL
- Dapper

## Architecture overview

One module, Orders, exposing minimal REST endpoints for order creation
and lookup. Used as the simplest Phase-2 happy-path fixture.

<module name="Orders">

<entities>
### Order
Aggregate root for customer purchase requests.

```sql
CREATE TABLE orders (
  id           UUID PRIMARY KEY,
  customer_id  UUID NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('pending','approved','denied')),
  total_cents  BIGINT NOT NULL,
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
- customerId: Guid (required)
- totalCents: long (required, > 0)

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
