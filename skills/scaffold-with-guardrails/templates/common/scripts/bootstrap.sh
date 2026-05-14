#!/usr/bin/env bash
# Bootstrap: wire git hooks, verify prereqs, fetch pinned tools.
#
# Usage:
#   ./scripts/bootstrap.sh           # full bootstrap (online)
#   ./scripts/bootstrap.sh --offline # skip tool downloads (CI / paranoid mode)
#   ./scripts/bootstrap.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OFFLINE=0
for a in "$@"; do
  case "$a" in
    --offline) OFFLINE=1 ;;
    --help) echo "Usage: $0 [--offline]"; exit 0 ;;
    *) echo "Unknown arg: $a" >&2; exit 2 ;;
  esac
done

cd "$REPO_ROOT"

say()  { printf '[%d/7] %s\n' "$1" "$2"; }
fail() { printf '[FAIL] %s\n' "$1" >&2; exit 1; }

# TODO: fetch_tool — deliberate stub for v1. Future task implements:
#   parse .tools/manifest.toml -> resolve vendor URL per tool -> curl ->
#   sha256 -> compare to canonical sha256_{os}_{arch} -> install.
fetch_tool() {
  local tool="$1"
  echo "    (stub: would fetch $tool — see TODO in bootstrap.sh)"
}

# 1. Prereqs
say 1 "Checking prereqs..."
command -v git >/dev/null || fail "git not found"
git_ver=$(git --version | awk '{print $3}')
command -v python3 >/dev/null || fail "python3 not found"
py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
py_ok=$(python3 -c 'import sys; print(1 if sys.version_info >= (3,10) else 0)')
[ "$py_ok" = "1" ] || fail "python >= 3.10 required (have $py_ver)"
echo "    ok (git $git_ver, python $py_ver)"

# 2. Detect worktree
GIT_DIR=$(git rev-parse --git-dir)
GIT_COMMON_DIR=$(git rev-parse --git-common-dir)
if [ "$GIT_DIR" != "$GIT_COMMON_DIR" ]; then
  echo "    Worktree detected. Writing config to $GIT_COMMON_DIR"
fi

# 3. Tools (skipped if --offline)
if [ "$OFFLINE" = "1" ]; then
  say 2 "Skipping tool downloads (--offline)"
else
  say 2 "Downloading pinned binaries..."
  for tool in gitleaks trivy scc; do
    fetch_tool "$tool" || fail "$tool fetch failed"
  done
  say 3 "Installing pipx tools..."
  command -v pipx >/dev/null || python3 -m pip install --user pipx
  pipx install semgrep || true
  pipx install lizard || true
fi

# 4. Wire git hooks (idempotent)
say 4 "Wiring git hooks..."
if ! git config --get-all include.path 2>/dev/null | grep -q "^\.\./\.gitconfig\.gates$"; then
  git config --local include.path ../.gitconfig.gates
fi

# 5. Worktree symlink for .tools/
if [ "$GIT_DIR" != "$GIT_COMMON_DIR" ]; then
  MAIN_TOOLS="$(cd "$GIT_COMMON_DIR/.." && pwd)/.tools"
  if [ -d "$MAIN_TOOLS" ] && [ ! -e "$REPO_ROOT/.tools" ]; then
    ln -s "$MAIN_TOOLS" "$REPO_ROOT/.tools"
  fi
fi

# 6. Self-test
say 5 "Verifying wiring..."
if [ -x ".githooks/pre-commit" ]; then
  .githooks/pre-commit --self-test >/dev/null || fail "pre-commit self-test failed"
fi

# 7. Profile lookup
profile=$(grep -E '^profile' .gates.toml 2>/dev/null | head -1 | sed 's/.*"\(.*\)".*/\1/' || echo "standard")
[ -z "$profile" ] && profile="standard"

cat <<EOF

Gates active. Profile: $profile.
Bypass: git commit --no-verify  (logs as Verified: no)
EOF
