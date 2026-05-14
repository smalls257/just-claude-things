#!/usr/bin/env pwsh
# Bootstrap (Windows): wire git hooks, verify prereqs, fetch pinned tools.
#
# Usage:
#   .\scripts\bootstrap.ps1              # full bootstrap (online)
#   .\scripts\bootstrap.ps1 -Offline     # skip tool downloads
#   .\scripts\bootstrap.ps1 -Help
[CmdletBinding()]
param(
  [switch]$Offline,
  [switch]$Help
)
$ErrorActionPreference = 'Stop'

if ($Help) { Write-Host "Usage: bootstrap.ps1 [-Offline]"; exit 0 }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir '..')
Set-Location $RepoRoot

function Say($n, $msg) { Write-Host "[$n/7] $msg" }
function Fail($msg) { Write-Error "[FAIL] $msg"; exit 1 }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# TODO: Fetch-Tool — deliberate stub for v1. Future task implements:
#   parse .tools/manifest.toml -> resolve vendor URL per tool -> Invoke-WebRequest ->
#   Get-FileHash -> compare canonical sha256_{os}_{arch} -> install.
function Fetch-Tool($tool) {
  Write-Host "    (stub: would fetch $tool — see TODO in bootstrap.ps1)"
}

# 1. Prereqs
Say 1 "Checking prereqs..."
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Fail "python not found" }
$py = python -c "import sys; print(sys.version_info >= (3,10))"
if ($py -ne "True") { Fail "python >= 3.10 required" }
$gitVer = (git --version).Split(' ')[2]
Write-Host "    ok (git $gitVer, python >= 3.10)"

# 2. Worktree detection
Say 2 "Detecting worktree..."
$gitDir       = git rev-parse --git-dir
$gitCommonDir = git rev-parse --git-common-dir
if ($gitDir -ne $gitCommonDir) {
  Write-Host "    Worktree detected. Common dir: $gitCommonDir"
} else {
  Write-Host "    Primary checkout."
}

# 3. Pinned binaries
if ($Offline) {
  Say 3 "Skipping binary downloads (-Offline)"
} else {
  Say 3 "Downloading pinned binaries..."
  foreach ($t in @('gitleaks','trivy','scc')) { Fetch-Tool $t }
}

# 4. pipx installs
if ($Offline) {
  Say 4 "Skipping pipx installs (-Offline)"
} else {
  Say 4 "Installing pipx tools..."
  if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    python -m pip install --user pipx
  }
  if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Fail "pipx installed to user-site but not on PATH; add %APPDATA%\Python\PythonXY\Scripts and re-run bootstrap"
  }
  # Visible warnings instead of silent fallback
  try { pipx install semgrep } catch { Warn "semgrep install failed; gates will report missing tool when run" }
  try { pipx install lizard  } catch { Warn "lizard install failed; gates will report missing tool when run" }
}

# 5. Wire git hooks (idempotent)
Say 5 "Wiring git hooks..."
$existing = git config --get-all include.path 2>$null
if ($existing -notcontains '../.gitconfig.gates') {
  git config --local include.path '../.gitconfig.gates'
}

# 6. Worktree junction for .tools/
# Note: assumes main repo was bootstrapped first (its .tools/ exists).
# If not, the junction is silently skipped and tools will be re-fetched.
Say 6 "Worktree symlink..."
if ($gitDir -ne $gitCommonDir) {
  $mainTools     = Join-Path (Split-Path $gitCommonDir -Parent) '.tools'
  $worktreeTools = Join-Path $RepoRoot '.tools'
  if ((Test-Path $mainTools) -and (-not (Test-Path $worktreeTools))) {
    New-Item -ItemType Junction -Path $worktreeTools -Target $mainTools | Out-Null
    Write-Host "    junction created: $worktreeTools -> $mainTools"
  } else {
    Write-Host "    n/a"
  }
} else {
  Write-Host "    n/a (primary checkout)"
}

# 7. Self-test + summary
Say 7 "Verifying wiring..."
$preCommit = Join-Path '.githooks' 'pre-commit'
if (Test-Path $preCommit) {
  # On Windows, git hooks shell out via bash (Git for Windows ships one).
  & bash $preCommit --self-test | Out-Null
  if ($LASTEXITCODE -ne 0) { Fail "pre-commit self-test failed" }
} else {
  Warn ".githooks/pre-commit not found; skipping self-test"
}

$profileLine = (Select-String -Path .gates.toml -Pattern '^profile' -ErrorAction SilentlyContinue | Select-Object -First 1).Line
if ($profileLine) {
  $profile = $profileLine -replace '.*"(.*)".*','$1'
} else {
  $profile = "standard"
}

Write-Host ""
Write-Host "Gates active. Profile: $profile."
Write-Host "Bypass: git commit --no-verify  (logs as Verified: no)"
