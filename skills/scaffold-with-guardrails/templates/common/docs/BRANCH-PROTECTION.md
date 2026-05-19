# Recommended branch protection

The gate system is the first line of defence. GitHub branch protection is the
second. Apply the following settings via repo Settings → Branches → Add rule
for `main`:

- ☑ Require a pull request before merging
  - ☑ Require approvals (≥ 1)
  - ☑ Dismiss stale approvals when new commits are pushed
- ☑ Require status checks to pass before merging
  - If `gates-backstop.yml` is enabled, add `verify` as required check
- ☑ Require linear history
- ☑ Restrict who can push to matching branches (admins only, for emergency bypass)
- ☑ Do not allow force pushes
- ☑ Do not allow deletions

Not auto-applied. Repo admin sets these once after first push.
