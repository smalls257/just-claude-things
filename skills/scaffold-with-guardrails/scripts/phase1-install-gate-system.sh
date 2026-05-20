#!/usr/bin/env bash
# Phase-1 gate-system installer.
# Invoked by scaffold.md's "Gate system installation (always)" step.
# Runs deterministically: every action is named, post-conditions logged.
# Exits non-zero on first failure (set -euo pipefail). Run from repo root.
#
# Required env var: SCAFFOLD (absolute path to skills/scaffold-with-guardrails/)
set -euo pipefail

if [ -z "${SCAFFOLD:-}" ]; then
  echo "ERROR: SCAFFOLD env var must be set to skills/scaffold-with-guardrails/ root" >&2
  exit 2
fi
if [ ! -d "$SCAFFOLD/templates/common" ]; then
  echo "ERROR: \$SCAFFOLD=$SCAFFOLD does not contain templates/common/" >&2
  exit 2
fi

log() { printf '[install-gate-system] %s\n' "$*"; }

# Language-agnostic
# Use `cp -R <src>/. <dst>/` (trailing `/.`) for directory copies — bare
# `cp -R <src> <dst>` on macOS nests src *inside* dst on re-run, which makes
# the scaffold non-idempotent and silently produces .githooks/githooks/...
log "step 1: copy language-agnostic common templates (editorconfig, githooks, scripts, gates config, tools manifest)"
cp "$SCAFFOLD/templates/common/.editorconfig" .
mkdir -p .githooks       && cp -R "$SCAFFOLD/templates/common/githooks/."     .githooks/
mkdir -p scripts         && cp -R "$SCAFFOLD/templates/common/scripts/."      scripts/
cp    "$SCAFFOLD/templates/common/gitconfig-gates"     .gitconfig.gates
cp    "$SCAFFOLD/templates/common/gates.toml.example"  .gates.toml
mkdir -p .tools
cp "$SCAFFOLD/templates/common/tools/manifest.toml.template" .tools/manifest.toml
cp "$SCAFFOLD/templates/common/tools/gitignore-template"     .tools/.gitignore

log "step 2: copy semgrep packs (csharp verbatim; OWASP filtered)"
mkdir -p .semgrep/packs
# csharp.yaml is already C#-only — copy verbatim.
cp "$SCAFFOLD/templates/common/semgrep-packs/csharp.yaml" .semgrep/packs/
# owasp-top-ten.yaml vendors 544 rules across 25 languages. Filter at copy
# time to the C#-applicable subset (csharp / C# / generic / yaml /
# dockerfile / regex / json / bash). Drops the pack from ~1.3 MB to ~190 KB
# and stops semgrep from loading 467 inert python/java/go/php/ruby/scala/
# kotlin/swift/clojure/solidity/hcl/terraform/html rules on every gate run.
# When the python / typescript scaffolds land, copy this block with a
# different KEEP set; do NOT mutate the vendored common/ file.
# PyYAML prereq — `python3 -c 'import yaml'` only ships with PyYAML
# installed (it's not in the stdlib). Guard the import so the scaffold
# fails loudly with an actionable message instead of a generic
# `ModuleNotFoundError: No module named 'yaml'` mid-script.
python3 -c 'import yaml' 2>/dev/null || {
    echo "PyYAML required for OWASP pack filtering. Installing via pip3..."
    pip3 install --quiet --user pyyaml || {
        echo "ERROR: pip3 install pyyaml failed. Install manually and retry."
        exit 1
    }
}

SRC="$SCAFFOLD/templates/common/semgrep-packs/owasp-top-ten.yaml" \
DST=".semgrep/packs/owasp-top-ten.yaml" \
python3 - <<'PY'
import os, yaml
KEEP = {'csharp', 'C#', 'generic', 'yaml', 'dockerfile', 'regex', 'json', 'bash'}
with open(os.environ['SRC']) as f:
    pack = yaml.safe_load(f)
pack['rules'] = [r for r in pack['rules'] if set(r.get('languages', []) or []) & KEEP]
with open(os.environ['DST'], 'w') as f:
    yaml.safe_dump(pack, f, sort_keys=False, default_flow_style=False, width=4096)
print(f"Filtered OWASP pack -> {len(pack['rules'])} C#-applicable rules")
PY

log "step 3: copy governance docs and PR template"
cp    "$SCAFFOLD/templates/common/docs/BYPASS-POLICY.md"      BYPASS-POLICY.md
cp    "$SCAFFOLD/templates/common/docs/BRANCH-PROTECTION.md"  BRANCH-PROTECTION.md
mkdir -p docs
cp "$SCAFFOLD/templates/common/docs/rules-audit.md.template" docs/rules-audit.md
mkdir -p .github
cp "$SCAFFOLD/templates/common/.github/PULL_REQUEST_TEMPLATE.md" .github/
mkdir -p .github/workflows
cp "$SCAFFOLD/templates/common/github-workflows/gates-backstop.yml.disabled" .github/workflows/
cp "$SCAFFOLD/templates/common/github-workflows/tools-pin-check.yml"          .github/workflows/

# .NET-conditional
log "step 4: copy .NET-conditional workflows + configs (Stryker, openapi-diff, coverlet)"
cp "$SCAFFOLD/templates/csharp/github-workflows/stryker-nightly.yml" .github/workflows/
cp "$SCAFFOLD/templates/csharp/github-workflows/openapi-diff.yml.disabled" .github/workflows/
cp "$SCAFFOLD/templates/csharp/stryker-config.json" .
cp "$SCAFFOLD/templates/csharp/coverlet.runsettings" .

# Make executables
log "step 5: chmod +x githooks and scripts"
chmod +x .githooks/pre-commit .githooks/pre-push .githooks/commit-msg
chmod +x .githooks/pre-commit.d/* .githooks/pre-push.d/* .githooks/commit-msg.d/*
chmod +x scripts/*.sh

# Stryker.NET tool install.
#
# Write a project-scoped NuGet.Config at the repo root BEFORE running
# `dotnet tool install`. `<clear/>` drops every source inherited from
# the user's global NuGet.Config; `<add ... nuget.org />` is then the
# only feed any `dotnet` command run from this directory will consult.
#
# Do NOT rely on `dotnet tool install --source ...` for this. The
# `--source` flag does not actually prevent feed enumeration: NuGet
# still walks every source in the effective config, and if any of them
# (e.g. an Azure DevOps `msft_consumption` upstream feed) returns 401
# before nuget.org is reached, the install fails — even though
# nuget.org has the package. That is a Silent Fallback: the flag looks
# like it constrains the install, but it does not. A project-scoped
# NuGet.Config with `<clear/>` is the canonical, authoritative override.
# dotnet-stryker is published only on nuget.org; there is no reason to
# consult any private feed for it.
#
# Symptoms this prevents (grep-bait for future debuggers):
#   error NU1301: Unable to load the service index for source
#     https://pkgs.dev.azure.com/.../_packaging/msft_consumption/nuget/v3/index.json
#   Response status code does not indicate success: 401 (Unauthorized)
#
# protocolVersion="3" pins the NuGet v3 API (v2 is deprecated; v3 is
# what every current nuget.org client speaks).
log "step 6: emit project-scoped NuGet.Config (Silent-Fallback override of inherited feeds)"
cat > NuGet.Config <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
</configuration>
EOF

log "step 7: dotnet new tool-manifest (idempotent) + dotnet tool install dotnet-stryker (idempotent)"
dotnet new tool-manifest 2>/dev/null || true
# `dotnet tool install` errors with "Tool 'dotnet-stryker' is already installed"
# on re-run, which would abort under `set -e`. The verifier instructs humans to
# re-run this script on failure, so we must survive a second run cleanly.
# Pattern: check the manifest first, install only if absent. `dotnet tool list`
# (without --global) reads `.config/dotnet-tools.json`.
if dotnet tool list 2>/dev/null | awk 'NR>2 {print $1}' | grep -qx 'dotnet-stryker'; then
  log "  dotnet-stryker already installed; skipping"
else
  dotnet tool install dotnet-stryker
fi

# Run bootstrap to wire hooks + fetch tools
log "step 8: ./scripts/bootstrap.sh (wire hooks + fetch tools)"
./scripts/bootstrap.sh

log "install complete"
