# Bypass Policy

The gate system exposes two intentional escape hatches:

1. **`git commit --no-verify`** — native git, skips pre-commit + commit-msg entirely.
2. **`GATES_SKIP=<csv> git commit`** — dispatcher env, skips named gates only.

Both are tracked in the `Verified:` trailer on the commit, or by trailer absence (`--no-verify`).

## Legitimate bypasses

- **Emergency hotfix** under outage pressure when a gate wrongly blocks. Document in PR description; remediate the false positive afterwards.
- **WIP commits on local branches** that you will squash/rebase before push.
- **Tool outage** (network failure pulling trivy DB). Skip the specific gate; CI nightly catches what was skipped.

## Illegitimate bypasses

- Avoiding test failures. Fix the test or the code.
- Silencing semgrep findings. Either fix, or document with `// nosemgrep: <rule-id> -- <reason>`.
- Pushing past gitleaks. **Rotate the leaked secret first**, then rewrite history.
- Routine convenience. If a gate is always wrong for your context, change the rule — don't bypass it.

## Reviewer responsibility

PRs containing `Verified: no` or `Verified: partial` commits should be challenged unless:

- The PR carries the `unsafe-skip` label (set by a human reviewer, not the author).
- The bypass reason is documented in the PR description.

If `gates-backstop.yml` is enabled, this is enforced automatically.

## Audit query

```bash
git log --grep='Verified: no' --since='30 days ago'
git log --grep='Verified: partial' --since='30 days ago'
```
