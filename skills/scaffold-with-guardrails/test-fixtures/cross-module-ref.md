---
status: complete
slug: cross-ref-demo
---

# Cross-Module Ref — Tech Design

## Tech stack
- C# / .NET 9

## Architecture overview

Intentionally invalid fixture. Orders.Order prose declares a Customer-typed field instead of a Customer ID — violates Phase-2 pre-check P3 Rule 3 (cross-module refs must use primitive IDs).

<module name="Customers">

<entities>

### Customer

```sql
CREATE TABLE customers (
  id    UUID        PRIMARY KEY,
  name  TEXT        NOT NULL
);
```

</entities>

</module>

<module name="Orders">

<entities>

### Order

Aggregate root for purchase requests. Each Order has a **customer** field of type `Customer` (the Customers module's aggregate). This violates the cross-module rule — fields across modules must be Guid IDs, not entity references.

```sql
CREATE TABLE orders (
  id           UUID        PRIMARY KEY,
  customer_id  UUID        NOT NULL,
  total_cents  BIGINT      NOT NULL
);
```

</entities>

</module>
