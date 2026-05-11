# ADR-0001: Use PostgreSQL over an event store

**Status:** accepted
**Date:** 2026-05-11
**Slug:** expense-portal

## Context

The expense portal's approval lifecycle produces a natural stream of domain events: submission, approval, rejection, resubmission, payment. An event-sourcing architecture with an event store (e.g., EventStoreDB) would be a defensible fit — the audit log is effectively an event ledger, and claim versions are a natural projection of appended events.

However, the team is greenfield on this domain, the delivery window is 3 months, and the reporting requirements (spend by department and category, arbitrary date ranges, CSV export) demand flexible ad-hoc queries that are expensive to satisfy from event projections without a read-model maintenance burden. The organisation has existing PostgreSQL operational expertise and no existing event-store infrastructure.

## Decision

We use PostgreSQL as the sole persistence layer. The audit trail is modelled as an append-only `audit_events` table (no UPDATE or DELETE ever issued). Claim versions are explicit rows with a `parent_claim_id` foreign key. This gives us an immutable audit record and full version lineage without the infrastructure complexity of an event store, while keeping spend reports as straightforward SQL aggregations.

## Alternatives considered

- **EventStoreDB + read-model projections** — The audit log and version history map cleanly onto an event ledger, and the domain is event-shaped. Rejected because: projection maintenance doubles the write-path complexity; ad-hoc spend reporting requires a purpose-built read model that must be kept in sync; the team has no event-store operational experience; the 3-month timeline cannot absorb this infrastructure risk.
- **EventStoreDB for audit only, PostgreSQL for claims** — A hybrid that captures the audit advantage without full event sourcing. Rejected because two persistence technologies in a 3-month greenfield project multiplies operational surface; the append-only `audit_events` table gives equivalent immutability guarantees at zero infrastructure cost.

## Consequences

- **Positive:** Ad-hoc reporting queries are plain SQL aggregations. Single operational dependency. Schema migrations via EF Core are well-understood. Spend reports and dashboards do not require projection synchronisation.
- **Negative:** The audit log is not a first-class event stream — replay and projection patterns would require re-implementing from the `audit_events` table if the system later needs event-driven integrations. The domain's natural event shape is slightly flattened into a relational model.
- **Reversibility cost:** Migrating to an event store later would require exporting `audit_events` and `claims` into an event stream, standing up event-store infrastructure, and rewriting the write path. Estimated cost: 4–6 weeks of engineering effort. This is a meaningful but not catastrophic reversal — worth noting now so the decision is not forgotten.
