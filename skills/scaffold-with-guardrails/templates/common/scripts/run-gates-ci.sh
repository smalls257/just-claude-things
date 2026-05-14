#!/usr/bin/env bash
# Replay pre-commit gates over a commit range in CI.
set -euo pipefail

RANGE="${1:-}"

usage() {
  cat <<EOF
Usage: run-gates-ci.sh <base>..<head>
Replays pre-commit gates over the diff in the given range.
EOF
}

if [ "$RANGE" = "--help" ]; then
  usage
  exit 0
fi
if [ -z "$RANGE" ]; then
  usage >&2
  exit 1
fi

# Verify wiring
git config --get-all include.path | grep -q "\.gitconfig\.gates" || \
  git config --local include.path ../.gitconfig.gates

# Replay each commit's content through pre-commit gates
fail=0
for sha in $(git rev-list "$RANGE"); do
  echo "=== Commit $sha ==="
  if ! parent=$(git rev-parse "$sha^" 2>/dev/null); then
    echo "Skipping root commit $sha (no parent)"
    continue
  fi
  git stash -u --quiet || true
  git checkout --quiet "$sha"
  # Stage all files (simulate pre-commit context)
  git -c core.hooksPath=/dev/null reset --soft "$parent"
  if ! .githooks/pre-commit; then
    fail=1
  fi
  git checkout --quiet -
  # Don't mute stderr — pop conflicts must stay visible. Empty stash is safe.
  git stash pop --quiet || echo "stash pop skipped (likely no stash or conflict)"
done
exit "$fail"
