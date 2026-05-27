# Phase-2 output fixtures

These files document the **expected** Phase-2 output for small inputs. They
are not consumed by an emitter today — the canonical flow is the
TaskCreate-driven subagent loop in `templates/csharp/scaffold-phase-2.md` —
but they pin the contract the subagent (or any future deterministic
emitter) must satisfy.

## What each fixture proves

- `expected-entity-with-string-prop.cs` — bug #4: non-nullable `string`
  property carries `= default!;` so CS8618 does not fire under
  `TreatWarningsAsErrors=true`. Value-type props (`Guid Id`,
  `DateTimeOffset CreatedAt`) have no initializer.

- `expected-contract-with-enum-ref.cs` — bug #5: a contract that references
  a Domain enum (`ReadingStatus`) carries
  `using Library.Domain.Catalog;` so the build resolves the type.
