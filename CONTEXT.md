# Project Context

> Domain glossary and shared mental model. Update when a term gets resolved or reframed.

## Glossary

### Claim
**Definition:** A request for reimbursement submitted by an employee for expenses incurred. Contains one or more itemized line items (description, category, amount, currency) and supporting receipt attachments. A claim has a single current status and may have multiple versions if it has been rejected and resubmitted.
**Not to be confused with:** A line item (a single expense row within a claim), or a version (a distinct revision of a claim after rejection).
**Examples:** An employee submits a claim for a client dinner (one line item, £320, GBP) with a photo receipt attached. Another employee submits a claim with three line items totalling €1,200 across two categories.

### Auto-approval
**Definition:** Automatic transition of a claim to Approved status without human review, triggered when the claim's GBP-equivalent total is below £500. The approval is recorded in the audit log with actor = System and requires no approver action.
**Not to be confused with:** A manual approval by a manager or VP.
**Examples:** A claim for £320 moves directly from Submitted to Approved. A claim for £499.99 (GBP) is auto-approved. A claim for £500.00 is not — it requires manager sign-off.

### Approval workflow
**Definition:** The sequential routing path a claim takes from submission to a final Approved or Rejected decision. Routing is determined by the GBP-equivalent total at submission: under £500 → auto-approve; £500–£5,000 → manager must decide; over £5,000 → manager approves first, then VP must decide. Each resubmission after rejection resets the workflow from the beginning.
**Not to be confused with:** The audit log (which records what happened) or the claim status (which shows the current position in the workflow).
**Examples:** A £3,200 claim enters PendingManagerApproval. The manager approves it and it moves to Approved. A £7,000 claim enters PendingManagerApproval; after manager approval it moves to PendingVPApproval.

### Rejection
**Definition:** A decision by a manager or VP to decline a claim, optionally accompanied by a comment explaining the reason (e.g., missing receipt, policy violation). A rejection moves the claim status to Rejected and prevents payment. The employee is notified and may edit and resubmit the claim.
**Not to be confused with:** A system validation error at submission time, which is a different failure path and does not create an audit event.
**Examples:** Manager rejects a claim with comment "Receipt image is unreadable." VP rejects a claim with comment "Amount exceeds category budget."

### Version
**Definition:** A distinct revision of a claim. Version 1 is the original submission. Each time an employee resubmits a rejected claim, a new version is created (incrementing version number) with a reference to the prior version via parent_claim_id. All versions are preserved permanently. The approval workflow restarts fresh for each new version.
**Not to be confused with:** A claim status update (which changes the state of a single version, not the version count).
**Examples:** Claim ABC starts as v1 (Rejected), employee edits and resubmits as v2 (Approved). Finance can view both v1 and v2 with their respective rejection reasons.

### Audit log
**Definition:** An immutable, append-only record of every state transition a claim passes through. Each entry captures: which claim, which actor took the action, what event occurred, when, and optionally why. Visibility is role-scoped: Finance sees all events, managers see events for their team's claims, employees see events for their own claims only. No entry is ever modified or deleted.
**Not to be confused with:** The claim's current status (a snapshot) or version history (the structural lineage of edits).
**Examples:** Audit entry: claimId=ABC, actor=Manager Jane, event=Rejected, reason="Missing receipt", timestamp=2026-04-10T14:32:00Z.

### Exchange rate
**Definition:** The GBP equivalent of the original claimed amount, fixed at the moment of submission. Sourced from ECB daily rates. Once recorded on a claim, this rate is immutable — it cannot be changed after submission, even if the market rate changes. Used for audit, reconciliation, and reporting. All internal processing and reporting uses the GBP equivalent.
**Not to be confused with:** A live or current market rate (which changes continuously). The rate on the claim is the rate at submission time, period.
**Examples:** Employee submits a €1,200 claim on 10 April 2026. ECB rate that day is 0.855 GBP/EUR. The claim records originalCurrency=EUR, totalAmountOriginal=1200.00, exchangeRateToGbp=0.855000, totalAmountGbp=1026.00. These values never change.

### Approval tier
**Definition:** The level of human approver required for a claim, determined by the GBP-equivalent total. Three tiers exist: Auto (no human required, < £500), Manager (£500–£5,000), and VP (> £5,000, after manager approval). Tier is resolved once at submission time using the immutable GBP total.
**Not to be confused with:** A claim status (which reflects where the claim currently is) or an approver role (which is the person's identity in the org).
**Examples:** A £4,999 claim has tier=Manager. A £5,001 claim has tier=VP (but must pass through Manager first).

### Employee snapshot
**Definition:** A point-in-time copy of an employee's record from Workday, including name, email, department, manager, and VP chain. Refreshed daily. Used by the portal to resolve org hierarchy without depending on Workday availability at request time. Historical claims retain a reference to the snapshot that was current at submission; snapshots are anonymised (not deleted) after 7 years per GDPR retention rules.
**Not to be confused with:** The live Workday record, which is the system of record. The snapshot may lag up to 24 hours.
**Examples:** If a manager changes on 11 April, claims submitted on 10 April still reference the prior manager snapshot. The new manager snapshot is picked up in the next daily sync.

## Boundaries

**This project owns:**
- Claim submission, status tracking, and receipt storage
- Approval routing and decision recording
- Immutable audit log with role-based visibility
- Spend reporting by department and category
- Manager pending-approvals dashboard
- Daily employee snapshot from Workday

**This project consumes:**
- Workday (employee and org hierarchy — read-only daily sync)
- Company SSO (authentication and identity — OAuth2/OIDC token validation)
- ECB daily exchange rates (rate at submission time)
- Object storage (receipt file storage)

**This project does not concern itself with:**
- Payment execution or General Ledger integration (Finance marks claims Paid; GL is out of scope)
- Mobile application
- Mileage tracking
- Legacy email or spreadsheet submission (no migration of historical claims)
- Any expense category not submitted through the portal

## Conventions

- All monetary amounts stored and reported in GBP equivalent; original currency and exchange rate also stored for audit.
- All primary keys are UUIDs; no sequential integer IDs exposed to clients.
- Timestamps are stored as TIMESTAMPTZ (UTC); displayed in user's local timezone by the frontend.
- Claim version numbering starts at 1 and increments per resubmission; gaps are not allowed.
- Role names in code and API: `Employee`, `Manager`, `VP`, `Finance` — match the requirements doc exactly.
- Status enum values: `Submitted`, `PendingManagerApproval`, `PendingVPApproval`, `Approved`, `Rejected`, `Paid` — no abbreviations or synonyms.
