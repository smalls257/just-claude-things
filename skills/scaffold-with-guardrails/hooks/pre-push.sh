#!/usr/bin/env bash
# Claude-only pre-push hook — wired via .claude/settings.json PreToolUse on git push.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if command -v dotnet >/dev/null 2>&1 && ls **/*.csproj >/dev/null 2>&1; then
  echo "→ dotnet test (Unit only)"
  dotnet test --filter "FullyQualifiedName~Tests.Unit" --nologo
fi

if [ -f "pyproject.toml" ] || [ -f "pytest.ini" ]; then
  echo "→ pytest -q"
  pytest -q -x
fi
