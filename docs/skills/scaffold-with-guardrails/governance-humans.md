# Governance: Humans

The gate system and Claude's operating rules handle a significant portion of
enforcement automatically. This document covers the human side of the same
governance loop: what reviewers are expected to read before commenting, what the
PR template forces authors to state explicitly, how branch protection encodes the
"no merge without eyes" rule, and how the rules audit closes the loop on
permitted bypasses.

See also: [governance-claude.md](governance-claude.md) for Claude-side
obligations, and [gates.md](gates.md) for the full gate catalogue.

---

## CLAUDE.md and AGENTS.md are not Claude-only

`CLAUDE.md` (project-level) and every directory-level `AGENTS.md` declare the
architecture in human-readable prose. They name the Six Principles in force,
the Violations those rules are designed to prevent, and the constraints that
apply to the module at hand. They are the contract. The code is an expression
of that contract; the contract is not derived from the code.

Reviewing a PR without first reading the `AGENTS.md` for the module being
touched is reviewing only the implementation, not the agreement it is supposed
to honour. A change can be locally coherent and globally wrong — it can follow
the existing code style while violating a constraint that only appears in the
`AGENTS.md`. Before commenting on a PR, open the `AGENTS.md` for every
directory with changed files and read it. If the change conflicts with a stated
constraint, name the constraint in your review comment, not just the symptom.
This is not optional ceremony; it is the only way to catch **Forensic Coding**
and **Leaky Narrative** violations before they accumulate into a system that
nobody can safely modify.

---

## PR template

Source:
`../../../skills/scaffold-with-guardrails/templates/common/.github/PULL_REQUEST_TEMPLATE.md`

Every PR opened in a scaffolded repo renders a structured template that forces
the author to make intent and gate compliance explicit before requesting review.
The template is not a checklist for its own sake — each section targets a
specific failure mode. The **Why** section prevents **Forensic Coding** by
requiring the business reason to be visible alongside the code change. The Six
Principles checklist surfaces **Leaky Narrative** and **Infected Core** before
a reviewer has to hunt for them. The Gates section closes the **Silent
Fallback** risk of a reviewer assuming the gates ran when they did not.

The template contains the following sections and checklist items (verbatim from
source):

**Six Principles check** — author self-certifies each Principle:

```
- [ ] **Anchor** — the *why* is visible in code (comments where non-obvious, descriptive names)
- [ ] **Shield** — units remain independently replaceable
- [ ] **Filter** — call sites read in domain language, not implementation tour
- [ ] **Buffer** — no new infrastructure dependency leaked into the core
- [ ] **Sensor** — failures observable without a debugger
- [ ] **Engine** — no obvious computational waste introduced
```

**Tests** — enumerates test layers including mutation score:

```
- [ ] Unit tests added / updated
- [ ] Integration tests (if cross-boundary)
- [ ] Architecture test (if new layer / dependency rule)
- [ ] Mutation score not regressed (review nightly Stryker artifact for new code)
```

**Gates** — the explicit gate-ran confirmation:

```
- [ ] Pre-commit gates green locally (`Verified: yes` on every commit)
- [ ] No `Verified: no` commits without `unsafe-skip` label
- [ ] `gates-backstop` workflow passing
```

**Risk + rollback** — a free-text field for production-affecting changes,
migrations, and feature flags, with a stated rollback path. This is the
**Sensor** discipline applied to the change itself: a rollback plan written
before merge is a plan; a rollback plan written during incident is a guess.

**Reviewer focus** — a free-text field that steers reviewers toward the
load-bearing files and away from generated ones. This is how authors prevent
reviewers from spending review time on scaffolding output rather than the
decision being made.

An unchecked item in the Gates section is a signal, not a blocker on its own —
but the reviewer must challenge it. An unchecked `Sensor` item on a change that
touches error-handling paths is a **Black Box** risk and warrants a hold. The
`unsafe-skip` label referenced in the Gates checklist is applied by a human
reviewer, not by the PR author — the author's job is to document why the
bypass is needed; the reviewer's job is to decide whether to grant it. This
asymmetry is what prevents the label from becoming self-service.

---

## Branch protection

Source:
`../../../skills/scaffold-with-guardrails/templates/common/docs/BRANCH-PROTECTION.md`

Branch protection is the second line of defence after the gate system. The gate
system enforces quality at commit time on the author's machine and in CI; branch
protection enforces that nothing enters `main` without passing both. The two
layers are not redundant — a force-push or a direct admin push can bypass the
gates entirely without branch protection.

The recommended configuration for the `main` branch (applied once by a repo
admin after first push — not auto-applied by the scaffold) is:

- **Require a pull request before merging**, with at least one required
  approval. Stale approvals are dismissed automatically when new commits are
  pushed, preventing a pattern where a reviewer approves a clean state and the
  author then lands a substantive change.
- **Require status checks to pass before merging.** When `gates-backstop.yml`
  is enabled, the `verify` check must be listed as required. This is what
  encodes the "what cannot be merged without human eyes and green CI" rule — it
  is not sufficient for the gates to have run locally; they must also pass in
  the CI environment.
- **Require linear history.** Merge commits obscure the per-commit `Verified:`
  trailer that the gate system writes; linear history keeps the audit trail
  readable.
- **Restrict who can push to matching branches** (admins only, for emergency
  bypass). Pairs with the bypass policy — even the emergency escape hatch is
  controlled.
- **Do not allow force pushes** and **do not allow deletions.** These two
  settings protect the `Verified:` audit trail from being rewritten after the
  fact.

Together these settings mean a `Verified: no` commit cannot silently become
part of `main` through a side channel. The `gates-backstop` required check is
what surfaces that trailer in CI, making the invisible visible and preventing
the **Black Box** failure mode at the merge boundary.

---

## Rules audit

Source:
`../../../skills/scaffold-with-guardrails/templates/common/docs/rules-audit.md.template`

The rules audit is a per-repo living document — instantiated from the template
above when the repo is first scaffolded — that tracks which vendored Semgrep
rule packs are in use, how each pack rule maps to the Violation Guide, where
overlap exists with the repo's custom rules, and which rules have been
promoted, demoted, or disabled since the last review. It is the mechanism that
prevents the gate configuration from drifting into **Fossil Comments** — rules
that fire loudly on patterns the team no longer considers dangerous, or that
duplicate a custom rule added six months later.

The audit template itself states the cadence — "Run quarterly to catch drift"
(line 4 of `rules-audit.md.template`). Its primary outputs are a set of
explicit promotion/demotion/disable decisions (not silent configuration edits)
and an effort log entry recording who reviewed, when, and what changed. The
quarterly cadence is the minimum; any significant rule change — adding a new
pack, rewriting a custom rule, or disabling a rule under bypass pressure —
should produce a same-day log entry rather than waiting for the scheduled
review.

The audit closes the governance loop on bypasses. When a rule is bypassed
repeatedly because it fires on a false positive, the right correction is to
narrow the rule (promote to `warn`, add path exclusions, or disable with an
explanation) and record that decision in the audit log. Leaving the rule in
place and accumulating `// nosemgrep:` annotations across the codebase is a
**Fossil Comments** failure mode: the rule appears active but has been
systematically neutered without a visible record of why.

The audit template ships with a sample Rule → Violation mapping table:

| Pack | Rule ID | Catches | Maps to |
|------|---------|---------|---------|
| owasp-top-ten | hardcoded-secret | embedded credentials | (covered by gitleaks; consider disabling here) |
| csharp | empty-catch | empty `catch {}` | Silent Fallback (already custom in `.semgrep/<app>/quality.yaml`) |
| csharp | use-startswith-instead | string ops | Computational Friction (low-value; demote/disable?) |

Fill this table during the first audit pass. An empty table is not a
compliant audit — it is a **Black Box** waiting to surprise the next person who
touches the Semgrep configuration.

The effort log at the bottom of the audit document records every review session
with a date, a reviewer name, and a brief note on what changed. This is not
bureaucracy — it is the diff of the governance layer itself. Without it, a rule
that was deliberately demoted six months ago looks identical to a rule that was
never reviewed; a future reviewer cannot distinguish intentional policy from
accidental configuration. The effort log makes the governance layer's own
history legible, which is the Anchor Principle applied to the rules themselves.

The audit also explicitly tracks which vendored pack rules duplicate existing
custom rules. Duplicate rules in different packs can fire on the same pattern
with different messages, producing noise that trains the team to dismiss gate
output — the earliest symptom of **Silent Fallback** at the governance layer.
Finding and disabling duplicates is one of the highest-value outputs of the
first audit pass.

---

## Bypass policy (cross-reference)

Full treatment lives in
[bypass-and-escape-hatches.md](bypass-and-escape-hatches.md) (lands in Task 7).

Bypassing a gate is permitted under specific, named conditions — emergency
hotfix under outage pressure, WIP squash-before-push, tool outage for a
specific gate — and is illegitimate for convenience, to silence findings, or to
avoid fixing a failing test. The `Verified:` trailer on every commit makes
every bypass visible in `git log`, and the audit log required by the rules
audit section above makes repeated bypasses visible across time. Visibility
without accountability is a **Silent Fallback**; the PR template's Gates
checklist and the `unsafe-skip` label requirement are what convert visibility
into accountability, closing the loop between the commit trailer, the PR
review, and the quarterly audit.
