---
slug: expense-portal
status: complete
deferred: []
last_session: 2026-05-11T00:00:00Z
prereqs: []
---

# Requirements — Expense Reimbursement Portal

## Problem

Employees currently submit expense claims via email to managers, attaching spreadsheets and receipt images. This process is slow, error-prone, and creates no audit trail. Finance teams manually consolidate claims and cannot easily track approvals or payment status. Managers lack visibility into pending claims and spend time chasing emails. The organisation needs a centralised system to streamline submission, approval, and payment processing.

## Users

- **Primary:** Employees submitting expense claims (submit receipts, track status)
- **Secondary:** Managers reviewing and approving team claims; Finance staff processing approved claims and generating spend reports

## Scope

**In:**
- Employees submit expenses with itemized details and receipt attachments
- Automatic approval for claims under £500
- Manager approval workflow for claims £500–£5,000
- VP approval required for claims over £5,000
- Approval/rejection with optional comments
- Employees resubmit rejected claims with edits; version history preserved
- Payment status tracking (submitted → approved → paid)
- Multi-currency support (GBP, EUR) with exchange rate recorded at submission
- Audit log visible to Finance (all transactions), managers (team only), employees (own only)
- Monthly spend reports by department and category for Finance
- Pending approvals dashboard for managers

**Out:**
- Mobile app
- General Ledger (GL) integration
- Mileage tracking
- Other expense categories not submitted via portal

## Functional requirements

### FR-001: Approval thresholds and auto-approval

The system routes expense claims based on amount. Claims under £500 are automatically approved. Claims from £500 to £5,000 require manager sign-off. Claims exceeding £5,000 require approval from both manager and VP. Each threshold acts as a routing gate; no human intervention is needed for claims below the first threshold.

### FR-002: Multi-currency and exchange rates

Employees may submit expenses in GBP or EUR. The system captures the exchange rate between the claimed currency and GBP (or organisational base currency) at the moment of submission. This rate is immutable and recorded alongside the claim for audit and reconciliation purposes.

### FR-003: Approval workflow with comments

Managers and VPs may approve or reject a claim. Rejection includes an optional comment explaining the reason (e.g., missing receipt, policy violation). The approver's decision, timestamp, and comment are logged. Rejections prevent payment and trigger a notification to the employee.

### FR-004: Rejection and resubmission with version history

When a claim is rejected, the employee may edit the claim and resubmit. The system preserves all previous versions and their rejection reasons, creating an audit trail of the claim's evolution. Each resubmission resets the approval workflow for that claim.

### FR-005: Payment status tracking

Each claim displays its current status: Submitted, Approved, Paid, or Rejected. Employees see this status on their own submissions. Finance sees status for all claims. The status updates as the claim moves through approval and payment processing.

### FR-006: Audit log with role-based visibility

All state changes (submission, approval, rejection, payment, resubmission) are logged with timestamp, actor, and reason. Finance can view the entire audit log. Managers see entries for their team's claims only. Employees see entries for their own claims only.

### FR-007: Spend reporting by department and category

Finance can generate reports showing total spend by department and expense category for any given month. Reports are queryable by date range and organisational unit. This enables cost analysis and budget tracking.

### FR-008: Manager dashboard for pending approvals

Managers see a dashboard listing all claims from their team awaiting their approval, sorted by amount and submission date. They can filter by status and access claim details without leaving the dashboard.

## Acceptance criteria

### FR-001
- [ ] Claims under £500 move to "Approved" status without manual intervention
- [ ] Claims £500–£5,000 enter "Pending Manager Approval" status
- [ ] Claims over £5,000 enter "Pending VP Approval" status after manager approval
- [ ] Threshold logic is transparent in system UI and audit log

### FR-002
- [ ] Employee selects currency (GBP or EUR) at submission
- [ ] System records the selected currency and GBP equivalent amount
- [ ] Exchange rate used is immutable and visible on the claim record
- [ ] Exchange rate is sourced from a defined reference point (e.g., daily rate at submission time)

### FR-003
- [ ] Approver can click "Approve" or "Reject"
- [ ] Reject action requires comment field (optional comment field is present)
- [ ] Approval/rejection timestamp and approver name are recorded
- [ ] Comment is visible to employee and Finance in audit trail

### FR-004
- [ ] Rejected claim status changes to "Rejected" with reason visible to employee
- [ ] Employee can edit rejected claim and resubmit (edits are allowed)
- [ ] System preserves original claim version and all edits as separate versions
- [ ] Version history is visible to Finance and employee
- [ ] Resubmitted claim re-enters approval workflow from the beginning

### FR-005
- [ ] Claim displays current status: Submitted, Approved, Paid, or Rejected
- [ ] Status updates are reflected in real-time or within seconds
- [ ] Employees see status for their own claims; Finance sees all statuses

### FR-006
- [ ] All state transitions logged: submission, approval, rejection, resubmission, payment
- [ ] Log entry includes actor, timestamp, status change, and reason (if applicable)
- [ ] Finance can view entire audit log for all claims
- [ ] Managers can view audit log for their team's claims only
- [ ] Employees can view audit log for their own claims only

### FR-007
- [ ] Finance can run report for any calendar month
- [ ] Report shows total spend by department and expense category
- [ ] Report output is CSV or similar exportable format
- [ ] Report sums are accurate and include all approved and paid claims in the period

### FR-008
- [ ] Manager dashboard displays all team claims awaiting manager or VP approval
- [ ] Dashboard shows claim amount, employee name, category, and submission date
- [ ] Manager can filter by status or sort by amount/date
- [ ] Manager can click to view full claim details without leaving dashboard

## Constraints

- Must integrate with Workday for employee, manager, and organisational hierarchy data
- Must comply with GDPR for personal data handling (employee names, email, claim history)
- Delivery timeline: 3 months from kickoff
- Claims submitted via portal only; no legacy email or spreadsheet submission after go-live

## Open questions

(None — all clarified in session.)

## Glossary

- **Claim** — A request for reimbursement submitted by an employee for expenses incurred. Contains itemized line items and supporting receipts.
- **Auto-approval** — Automatic transition to Approved status without human review, triggered by threshold logic.
- **Approval workflow** — Sequential routing: under £500 → auto-approve; £500–£5k → manager → approved or rejected; over £5k → manager → VP → approved or rejected.
- **Rejection** — Manager or VP decision to decline a claim, optionally with comment. Claim returns to employee for resubmission.
- **Version** — A distinct state of a claim; each resubmission after rejection creates a new version while preserving prior versions.
- **Audit log** — Immutable record of all state changes, visible according to role.
- **Exchange rate** — GBP equivalent of claim amount at submission time, recorded immutably for reconciliation.
