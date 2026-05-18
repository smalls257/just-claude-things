# Bypass and escape hatches

See also: [README.md](README.md) · [governance-humans.md](governance-humans.md) ·
[hooks.md](hooks.md) · [gates.md](gates.md)

---

## Why bypass at all

Gates are right most of the time and wrong some of the time. A tool network
outage, a false-positive semgrep finding on a hot-path rollback, or a
misconfigured local environment can block a commit that should have merged an
hour ago. A system with no sanctioned escape hatch does not produce perfect
compliance — it produces rule erosion. `git commit --no-verify` becomes muscle
memory; people stop reading `Verified:` trailers because the trailers stopped
meaning anything; the gate system decays into theatre while the real
enforcement moves to informal norms nobody can audit.

The discipline here is not "no bypass" — it is "no *silent* bypass." Every
bypass leaves a trail: `Verified: no` or `Verified: partial` in `git log`, an
explicit note in the PR description, and an entry in `docs/rules-audit.md`.
Visibility without accountability is **Silent Fallback** in governance clothing;
the audit trail is what converts visibility into accountability. A bypass that
cannot be found in `git log --grep='Verified: no'` is an unauthorized bypass,
full stop.

---

## Per-tool escape hatches

The table below maps each available escape mechanism to its scope, legitimate
use, and audit signal. Read the accuracy notes under the table before using any
of them.

| Escape | What it does | When legit | Audit trace |
|---|---|---|---|
| `git commit --no-verify` | Skips pre-commit + commit-msg entirely | Gate broken, urgent rollback, env misconfigured | `Verified:` trailer absent on commit |
| `git push --no-verify` | Skips pre-push hooks entirely | Same as above | No push-side trailer |
| `GATES_SKIP=<csv>` | Dispatcher env: skips only named gates | Specific gate hanging, tool outage (trivy DB, semgrep registry) | Commit gets `Verified: partial` trailer naming skipped gates |
| `GATES_DRY_RUN=1` | Dispatcher env: runs gates, reports verdicts without blocking | Debugging a gate, surveying impact before enabling in CI | Not a real bypass — verdicts reported, not enforced |
| `SKIP_SEMGREP=1` | MSBuild only: skips `SemgrepLint` target during `dotnet build` | Faster iteration when semgrep findings are noise and not committed | Build-time only; pre-commit semgrep still runs unless `--no-verify` |
| `[skip ci]` in commit msg | GitHub Actions skips workflow run for that push | Doc-only changes no CI gate covers | Reviewer confirms in PR |
| Branch protection override | Admin merges against required checks | Production incident requiring immediate rollback | GitHub timeline event records actor; post-incident write-up follows |

**Accuracy notes:**

`SKIP_SEMGREP=1` is MSBuild-only. It suppresses the `SemgrepLint` target in
`Directory.Build.targets` during a `dotnet build` run and has no effect on the
pre-commit hook. If you need to skip semgrep in the pre-commit hook, use
`GATES_SKIP=semgrep` (or `--no-verify` to skip all hooks). Conflating the two
produces a situation where the build is quiet but the commit still blocks —
which is confusing and wastes time diagnosing the "wrong" bypass.

`GATES_DRY_RUN=1` is not a bypass at all. Gates run in full; the dispatcher
simply does not exit non-zero on failure. Use it to understand what would block
before wiring a new gate into CI, not to land code past a failing gate. The
distinction matters: treating `GATES_DRY_RUN=1` as a bypass is **Silent
Fallback** — it looks like you ran the gates, and technically you did, but the
failures were discarded rather than addressed.

From `BYPASS-POLICY.md`, the full list of **legitimate** bypasses:

- Emergency hotfix under outage pressure when a gate wrongly blocks. Document
  in the PR description; remediate the false positive afterwards.
- WIP commits on local branches that you will squash or rebase before push.
- Tool outage (network failure pulling trivy DB). Skip the specific gate;
  CI nightly catches what was skipped.

And the **illegitimate** bypasses:

- Avoiding test failures. Fix the test or the code.
- Silencing semgrep findings. Either fix, or annotate with
  `// nosemgrep: <rule-id> -- <reason>`.
- Pushing past gitleaks. **Rotate the leaked secret first**, then rewrite
  history.
- Routine convenience. If a gate is always wrong for your context, change the
  rule — don't bypass it.

To find bypassed commits in a repo:

```bash
git log --grep='Verified: no' --since='30 days ago'
git log --grep='Verified: partial' --since='30 days ago'
```

Run these queries during PR review and during the quarterly audit. A spike in
`Verified: partial` for a specific gate is a signal that the gate is either
broken or miscalibrated — it is not a signal to normalize the bypass.

---

## Branch protection emergency-merge

`BRANCH-PROTECTION.md` restricts pushes to `main` to admins only. That
restriction is what makes this escape hatch work: only a named, accountable
person can exercise it. The process is not "force push" — force pushes are
explicitly disabled in the recommended configuration, protecting the
`Verified:` audit trail from being rewritten after the fact. The emergency
path is an admin approving and merging a PR against failing required checks via
the GitHub UI.

GitHub records the override as a timeline event on the PR, with the actor's
identity and timestamp. This is not invisible convenience — it is a
deliberate record. Anyone looking at the PR after the fact can see that the
`verify` check was not green at merge and who made the call. The record exists
whether or not anyone asks for it.

The merge is not the end of the obligation. Post-merge: an incident write-up
names which gate was bypassed, the business reason, and the expected timeline
for the fix-forward PR. The fix-forward PR should appear within one sprint. If
it does not, the quarterly audit surfaces it as an open bypass without
follow-through.

This section covers the emergency-merge dimension only. For standing branch
protection configuration — which checks are required, how stale approvals are
handled, why linear history is enforced — see `governance-humans.md`.

---

## Decision tree: bypass vs fix

```
Was the gate wrong?
├── Yes: was it a false positive?
│   ├── Yes → bypass with audit entry; file ticket to refine the rule
│   └── No (gate measures something we no longer want to enforce) → remove the rule, do not bypass
└── No: are you OK violating the rule?
    ├── Yes (urgent business need, accepted tech debt) → bypass with audit + follow-up ticket
    └── No → fix the code, do not bypass
```

The key distinction is whether the gate is wrong or whether you are shipping
code that does exactly what the gate exists to prevent. Treating the second as
the first is how rule erosion starts: each individual bypass looks defensible
in isolation, and collectively they hollow out the rule until only the
enforcement machinery remains, firing on a policy nobody believes in. A bypass
without a follow-up ticket is **Silent Fallback** — it restores velocity now
and silently accrues entropy that nobody is committed to fixing. The ticket is
not bureaucracy; it is the mechanism that prevents "temporary" from becoming
permanent.

---

## Audit trail

Every bypass is reflected in `docs/rules-audit.md` — the per-repo living
document instantiated from
`templates/common/docs/rules-audit.md.template` at scaffold time. Each entry
records the date, the gate bypassed, the reason, and the follow-up ticket or
expected resolution. For the full structure of that document and the quarterly
review cadence, see `governance-humans.md`'s Rules audit section.

On PR review, reviewers spot-check the gate trailers on every commit in the
branch. A `Verified: no` or `Verified: partial` commit without an accompanying
entry in the PR description is a hold, not a nit. The `unsafe-skip` label is
set by the reviewer, not the author — the author's job is to document why the
bypass is needed; the reviewer's job is to decide whether the reason is
legitimate. This asymmetry exists to prevent the label from becoming
self-service, which would make it indistinguishable from no label at all.

The quarterly retro question is: which gates account for the most bypasses
over the period? A gate that is bypassed repeatedly is either catching real
violations that the team is choosing to ignore (a discipline problem) or
producing false positives on common patterns (a calibration problem). Neither
situation improves by leaving the gate unchanged. Refine the rule, narrow its
scope, promote it from `error` to `warn`, or retire it — and record the
decision in the effort log so the next reviewer can distinguish intentional
policy from accidental configuration.
