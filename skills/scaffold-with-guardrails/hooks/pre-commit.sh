#!/usr/bin/env bash
# Claude-only pre-commit hook — wired via .claude/settings.json PreToolUse on git commit.
# Devs use their own git hooks independently.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if [ -d ".semgrep" ]; then
  echo "→ semgrep gate"
  semgrep scan --config .semgrep/ --error --quiet
fi

if command -v dotnet >/dev/null 2>&1 && ls **/*.csproj >/dev/null 2>&1; then
  echo "→ dotnet format"
  dotnet format --verify-no-changes
fi

last_msg=$(git log -1 --pretty=%s 2>/dev/null || true)
if [ -n "$last_msg" ]; then
  if ! echo "$last_msg" | grep -Eq '^(feat|fix|chore|docs|test|refactor|perf|build|ci)(\([^)]+\))?: '; then
    echo "warning: commit message does not match Conventional Commits pattern"
  fi
fi
