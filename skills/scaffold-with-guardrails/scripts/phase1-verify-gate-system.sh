#!/usr/bin/env bash
# Phase-1 gate-system post-condition verifier.
# Runs immediately after phase1-install-gate-system.sh from the target repo
# root. Collects ALL missing artifacts (does not stop on first failure) and
# emits a single batched report. Exits 0 if all present, 1 if any missing.
#
# This is the in-body sensor that closes the "subagent declared install
# done but skimmed a step" failure mode. Phase-2's pre-flight tripwire-1
# is the second line of defense; this is the first.
set -uo pipefail

FAIL=0
report_missing()        { echo "MISSING: $1" >&2; FAIL=1; }
report_not_executable() { echo "NOT EXECUTABLE: $1" >&2; FAIL=1; }

# Precondition from earlier `dotnet new sln` step (glob-safe form — `test -f
# *.sln` is a Silent Fallback when the glob has 0 or ≥2 matches).
ls *.sln >/dev/null 2>&1                                  || report_missing "*.sln"

# Language-agnostic common templates
test -f .editorconfig                                     || report_missing .editorconfig
test -f .githooks/pre-commit                              || report_missing .githooks/pre-commit
test -f .githooks/pre-push                                || report_missing .githooks/pre-push
test -f .githooks/commit-msg                              || report_missing .githooks/commit-msg
test -f scripts/bootstrap.sh                              || report_missing scripts/bootstrap.sh
test -f .gitconfig.gates                                  || report_missing .gitconfig.gates
test -f .gates.toml                                       || report_missing .gates.toml
test -f .tools/manifest.toml                              || report_missing .tools/manifest.toml

# Semgrep packs (csharp verbatim; owasp filtered to C#-applicable subset)
test -f .semgrep/packs/csharp.yaml                        || report_missing .semgrep/packs/csharp.yaml
test -f .semgrep/packs/owasp-top-ten.yaml                 || report_missing .semgrep/packs/owasp-top-ten.yaml

# Governance docs
test -f BYPASS-POLICY.md                                  || report_missing BYPASS-POLICY.md
test -f BRANCH-PROTECTION.md                              || report_missing BRANCH-PROTECTION.md
test -f docs/rules-audit.md                               || report_missing docs/rules-audit.md

# GitHub PR template + workflows
test -f .github/PULL_REQUEST_TEMPLATE.md                  || report_missing .github/PULL_REQUEST_TEMPLATE.md
test -f .github/workflows/gates-backstop.yml.disabled     || report_missing .github/workflows/gates-backstop.yml.disabled
test -f .github/workflows/tools-pin-check.yml             || report_missing .github/workflows/tools-pin-check.yml
test -f .github/workflows/stryker-nightly.yml             || report_missing .github/workflows/stryker-nightly.yml
test -f .github/workflows/openapi-diff.yml.disabled       || report_missing .github/workflows/openapi-diff.yml.disabled

# .NET-conditional configs
test -f stryker-config.json                               || report_missing stryker-config.json
test -f coverlet.runsettings                              || report_missing coverlet.runsettings
test -f NuGet.Config                                      || report_missing NuGet.Config

# Proves `dotnet new tool-manifest` + `dotnet tool install dotnet-stryker` ran
test -f .config/dotnet-tools.json                         || report_missing .config/dotnet-tools.json

# Executability — chmod step proves the hooks/scripts will actually fire
test -x .githooks/pre-commit                              || report_not_executable .githooks/pre-commit
test -x scripts/bootstrap.sh                              || report_not_executable scripts/bootstrap.sh

if [ "$FAIL" -ne 0 ]; then
  echo "" >&2
  echo "gate-system verification FAILED. Re-run phase1-install-gate-system.sh after fixing root cause." >&2
  exit 1
fi
echo "[verify-gate-system] all artifacts present"
