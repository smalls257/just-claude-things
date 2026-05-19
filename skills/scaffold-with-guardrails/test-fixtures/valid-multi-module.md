---
status: complete
slug: orders-multi
---

# Orders Multi-Module — Tech Design

## Tech stack
- C# / .NET 9
- PostgreSQL
- Dapper

## Architecture overview

Two business modules (Customers, Orders) plus a Shared kernel module for cross-cutting value objects (Money). Used as the canonical Phase-2 multi-module happy-path fixture.

<module name="Shared">

<entities>

### Money

Value object for currency amounts. Embedded as columns in owning tables; no own table.

```sql
-- Shared value object — embedded as columns in owning tables, no own table.
-- This is documentation only; no DDL emitted.
```

</entities>

</module>

<module name="Customers">

<entities>

### Customer

Aggregate root for customer profile data.

```sql
CREATE TABLE customers (
  id     UUID        PRIMARY KEY,
  email  TEXT        NOT NULL UNIQUE,
  name   TEXT        NOT NULL
);
```

</entities>

<contracts>

### CustomerResponse

- id: Guid
- email: string
- name: string

</contracts>

<endpoints>

### GET /customers/{id}

- Response: 200 CustomerResponse | 404

</endpoints>

</module>

<module name="Orders">

<entities>

### Order

Aggregate root for purchase requests. Customer linked by Guid ID, not by entity reference.

```sql
CREATE TABLE orders (
  id           UUID        PRIMARY KEY,
  customer_id  UUID        NOT NULL,
  status       TEXT        NOT NULL CHECK (status IN ('pending','approved','denied')),
  total_cents  BIGINT      NOT NULL
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
- totalCents: long — required, > 0

### OrderResponse

- id: Guid
- customerId: Guid
- status: OrderStatus
- totalCents: long

</contracts>

<endpoints>

### POST /orders

- Request: CreateOrderRequest
- Response: 201 OrderResponse

### GET /orders/{id}

- Response: 200 OrderResponse | 404

</endpoints>

</module>
