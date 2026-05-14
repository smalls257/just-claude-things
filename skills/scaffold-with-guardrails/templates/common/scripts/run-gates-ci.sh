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
ORIG=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || git rev-parse HEAD)
fail=0
for sha in $(git rev-list "$RANGE"); do
  echo "=== Commit $sha ==="
  if ! parent=$(git rev-parse "$sha^" 2>/dev/null); then
    echo "Skipping root commit $sha (no parent)"
    continue
  fi
  # Capture stash count to detect whether our push created a stash.
  stash_before=$(git stash list | wc -l)
  git stash -u --quiet || true
  stash_after=$(git stash list | wc -l)
  pushed_stash=0
  [ "$stash_after" -gt "$stash_before" ] && pushed_stash=1

  git checkout --quiet "$sha"
  # Stage all files (simulate pre-commit context)
  git -c core.hooksPath=/dev/null reset --soft "$parent"
  if ! .githooks/pre-commit; then
    fail=1
  fi
  git checkout --quiet "$ORIG"

  # Only pop if we pushed. Don't mute stderr — pop conflicts must stay visible.
  if [ "$pushed_stash" -eq 1 ]; then
    git stash pop --quiet
  fi
done
exit "$fail"
