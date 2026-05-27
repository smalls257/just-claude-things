---
status: complete
slug: malformed-demo
---

# Malformed Tags — Tech Design

## Tech stack
- C# / .NET 9

## Architecture overview

Intentionally malformed fixture. Used to verify PREREQ-CHECK step 5 fails loud on unbalanced `<module>` tags.

<module name="Orders">

<entities>

### Order

```sql
CREATE TABLE orders (id UUID PRIMARY KEY);
```

</entities>

<!-- <module> tag intentionally not closed. PREREQ-CHECK step 5 must catch this. -->
