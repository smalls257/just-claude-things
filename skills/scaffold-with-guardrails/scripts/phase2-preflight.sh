#!/usr/bin/env bash
# Phase-2 pre-flight gate.
# Three tripwires, run from target repo root:
#  1. Phase-1 artifact inventory (every file the gate-system writes)
#  2. `dotnet build` exits 0
#  3. `dotnet test --filter ~Architecture` exits 0
#
# Collects ALL failures into a single batched report (Sensor — fail loud,
# fail with full context). Exits 1 if any tripwire fails; 0 if all pass.
#
# The skill's guarantees (semgrep gates, NetArchTest, hooks, layered
# AGENTS.md guidance) depend on every artifact in tripwire 1 being
# present. A code-only scaffold with no governance is the failure mode
# this gate exists to prevent.
set -uo pipefail

FAIL=0
MISSING=()
report_missing() { MISSING+=("$1"); FAIL=1; }

BUILD_FAIL=""
TEST_FAIL=""

# ============================================================================
# Tripwire 1: Phase-1 artifact inventory
# ============================================================================
# `test -f *.sln` is a Silent Fallback (glob expands before `test` sees it).
# `ls *.sln >/dev/null 2>&1` collapses zero/one/many cases honestly.
ls *.sln >/dev/null 2>&1                                                                   || report_missing "*.sln"

# Language-agnostic + .NET-conditional root configs
test -f global.json                                                                         || report_missing "global.json"
test -f Directory.Build.props                                                               || report_missing "Directory.Build.props"
test -f Directory.Build.targets                                                             || report_missing "Directory.Build.targets"
test -f Directory.Packages.props                                                            || report_missing "Directory.Packages.props"
test -f coverlet.runsettings                                                                || report_missing "coverlet.runsettings"
test -f .editorconfig                                                                       || report_missing ".editorconfig"
test -f CLAUDE.md                                                                           || report_missing "CLAUDE.md"

# semgrep packs + per-layer rules
test -d .semgrep && [ "$(find .semgrep -name '*.yaml' 2>/dev/null | wc -l)" -gt 0 ]         || report_missing ".semgrep/*.yaml"
[ "$(find .semgrep -path '*/security.yaml' 2>/dev/null | wc -l)" -gt 0 ]                    || report_missing ".semgrep/*/security.yaml"
[ "$(find .semgrep -path '*/quality.yaml' 2>/dev/null | wc -l)" -gt 0 ]                     || report_missing ".semgrep/*/quality.yaml"
[ "$(find .semgrep -path '*/async.yaml' 2>/dev/null | wc -l)" -gt 0 ]                       || report_missing ".semgrep/*/async.yaml"
test -f .semgrep/packs/csharp.yaml                                                          || report_missing ".semgrep/packs/csharp.yaml"
test -f .semgrep/packs/owasp-top-ten.yaml                                                   || report_missing ".semgrep/packs/owasp-top-ten.yaml"

# Claude Code hooks
test -f .claude/settings.json                                                               || report_missing ".claude/settings.json"
test -f .claude/hooks/pre-commit.sh                                                         || report_missing ".claude/hooks/pre-commit.sh"
test -f .claude/hooks/pre-push.sh                                                           || report_missing ".claude/hooks/pre-push.sh"
test -f .github/PULL_REQUEST_TEMPLATE.md                                                    || report_missing ".github/PULL_REQUEST_TEMPLATE.md"

# Per-layer artifacts (≥1 of each)
[ "$(find src -maxdepth 2 -name 'AGENTS.md' 2>/dev/null | wc -l)" -gt 0 ]                   || report_missing "src/*/AGENTS.md"
[ "$(find src -maxdepth 2 -name 'AssemblyMarker.cs' 2>/dev/null | wc -l)" -gt 0 ]           || report_missing "src/*/AssemblyMarker.cs"
[ "$(find tests -path '*/Architecture/*ArchitectureTests.cs' 2>/dev/null | wc -l)" -gt 0 ]  || report_missing "tests/*.Tests.Unit/Architecture/*ArchitectureTests.cs"

# Gate-system layer (from Phase-1 harness — phase1-install-gate-system.sh)
test -f BYPASS-POLICY.md                                                                    || report_missing "BYPASS-POLICY.md"
test -f BRANCH-PROTECTION.md                                                                || report_missing "BRANCH-PROTECTION.md"
test -f .githooks/pre-commit                                                                || report_missing ".githooks/pre-commit"
test -f .githooks/pre-push                                                                  || report_missing ".githooks/pre-push"
test -f .githooks/commit-msg                                                                || report_missing ".githooks/commit-msg"
test -f scripts/bootstrap.sh                                                                || report_missing "scripts/bootstrap.sh"
test -f .tools/manifest.toml                                                                || report_missing ".tools/manifest.toml"
test -f .github/workflows/gates-backstop.yml.disabled                                       || report_missing ".github/workflows/gates-backstop.yml.disabled"
test -f .github/workflows/tools-pin-check.yml                                               || report_missing ".github/workflows/tools-pin-check.yml"
test -f .github/workflows/stryker-nightly.yml                                               || report_missing ".github/workflows/stryker-nightly.yml"
test -f .gates.toml                                                                         || report_missing ".gates.toml"
test -f .gitconfig.gates                                                                    || report_missing ".gitconfig.gates"
test -f stryker-config.json                                                                 || report_missing "stryker-config.json"
test -f NuGet.Config                                                                        || report_missing "NuGet.Config"
test -f docs/rules-audit.md                                                                 || report_missing "docs/rules-audit.md"

# ============================================================================
# Tripwire 2: Build is green
# ============================================================================
BUILD_LOG=$(mktemp)
if ! dotnet build > "$BUILD_LOG" 2>&1; then
  BUILD_FAIL=$(cat "$BUILD_LOG")
  FAIL=1
fi

# ============================================================================
# Tripwire 3: Architecture tests pass
# ============================================================================
TEST_LOG=$(mktemp)
if ! dotnet test --filter "FullyQualifiedName~Architecture" > "$TEST_LOG" 2>&1; then
  TEST_FAIL=$(cat "$TEST_LOG")
  FAIL=1
fi

# ============================================================================
# Batched failure report
# ============================================================================
if [ "$FAIL" -ne 0 ]; then
  cat >&2 <<'EOF'

Phase-2 pre-flight FAILED. Phase-1 is incomplete or broken.

Missing artifacts:
EOF
  if [ "${#MISSING[@]}" -eq 0 ]; then
    echo "  (none)" >&2
  else
    for m in "${MISSING[@]}"; do echo "  - $m" >&2; done
  fi

  echo "" >&2
  echo "Build/test failures:" >&2
  if [ -n "$BUILD_FAIL" ]; then
    echo "  dotnet build FAILED — verbatim output below:" >&2
    echo "$BUILD_FAIL" | sed 's/^/    /' >&2
  fi
  if [ -n "$TEST_FAIL" ]; then
    echo "  dotnet test --filter Architecture FAILED — verbatim output below:" >&2
    echo "$TEST_FAIL" | sed 's/^/    /' >&2
  fi
  if [ -z "$BUILD_FAIL" ] && [ -z "$TEST_FAIL" ]; then
    echo "  (none — only inventory failures)" >&2
  fi

  cat >&2 <<'EOF'

Resolution:
  - Re-run scaffold-with-guardrails Phase-1 to completion, OR
  - Hand-author the missing artifacts before re-invoking Phase-2.

Phase-2 will NOT proceed. A code-only scaffold with no governance is
the failure mode this gate exists to prevent.
EOF

  rm -f "$BUILD_LOG" "$TEST_LOG"
  exit 1
fi

rm -f "$BUILD_LOG" "$TEST_LOG"
echo "[phase2-preflight] all 3 tripwires PASSED"
exit 0
