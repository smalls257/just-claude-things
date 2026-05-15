#!/usr/bin/env bash
# UAT harness for bulletproof-gates. See docs/superpowers/specs/2026-05-15-uat-test-suite-design.md.
set -uo pipefail

# === Globals ===========================================================
UAT_ROOT="$(mktemp -d -t uat.XXXXXX)"
SCAFFOLD_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORIG_PATH="$PATH"
PASSED=()
FAILED=()
VERBOSE=0
LIVE=0
ONLY=""

# === Flag parsing ======================================================
while [ $# -gt 0 ]; do
  case "$1" in
    --verbose) VERBOSE=1; shift ;;
    --live) LIVE=1; shift ;;
    --only) ONLY="$2"; shift 2 ;;
    --help|-h)
      cat <<'EOF'
Usage: run-uat.sh [--verbose] [--live] [--only sNN_name]
  --verbose   Stream gate output to stderr
  --live      Use real tools instead of stubs (slow)
  --only ID   Run a single scenario
EOF
      exit 0
      ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$UAT_ROOT/logs"

# === Helpers (filled in Task 2-3) ======================================

assert_exit() {
  local expected="$1" actual="$2"
  if [ "$expected" != "$actual" ]; then
    echo "ASSERT FAIL: expected exit $expected, got $actual" >&2
    return 1
  fi
}

assert_output_contains() {
  local pattern="$1" output="$2"
  if ! echo "$output" | grep -qE "$pattern"; then
    echo "ASSERT FAIL: output missing pattern: $pattern" >&2
    echo "Output was:" >&2
    echo "$output" >&2
    return 1
  fi
}

assert_file_exists() {
  local path="$1"
  if [ ! -e "$path" ]; then
    echo "ASSERT FAIL: missing file: $path" >&2
    return 1
  fi
}

assert_trailer() {
  local expected="$1"
  local actual
  actual="$(git log -1 --format='%(trailers:key=Verified,valueonly,separator=)')"
  # Trailer format: "yes" or "no (failed: ...)" or "partial (skipped: ...)".
  # Compare only the leading word to ignore optional detail in parens.
  actual="${actual%% *}"
  if [ "$actual" != "$expected" ]; then
    echo "ASSERT FAIL: trailer Verified expected='$expected' got='$actual'" >&2
    return 1
  fi
}

assert_no_trailer() {
  local actual
  actual="$(git log -1 --format='%(trailers:key=Verified,valueonly,separator=)')"
  actual="${actual%% *}"
  if [ -n "$actual" ]; then
    echo "ASSERT FAIL: expected no Verified trailer, got '$actual'" >&2
    return 1
  fi
}

assert_gate_skipped() {
  local gate="$1"
  local lastrun=".git/gates-last-run"
  if [ ! -f "$lastrun" ]; then
    echo "ASSERT FAIL: no $lastrun" >&2
    return 1
  fi
  if ! grep -qE "^SKIPPED=.*${gate}" "$lastrun"; then
    echo "ASSERT FAIL: gate $gate not skipped in $lastrun" >&2
    cat "$lastrun" >&2
    return 1
  fi
}

# Bootstrap a fresh test repo from the scaffold template at $SCAFFOLD_ROOT.
# Args: <target_dir> [profile]
bootstrap_test_repo() {
  local target="$1" profile="${2:-standard}"
  mkdir -p "$target"
  (
    cd "$target"
    git init -q
    git config user.email "uat@example.com"
    git config user.name "UAT"
    # Stage scaffold template files into this repo.
    local src="$SCAFFOLD_ROOT/skills/scaffold-with-guardrails/templates/common"
    cp -R "$src/githooks" .githooks
    cp -R "$src/scripts" .
    cp "$src/gates.toml.example" .gates.toml
    sed -i.bak "s|profile = \"standard\"|profile = \"$profile\"|" .gates.toml
    rm -f .gates.toml.bak
    chmod +x .githooks/pre-commit .githooks/pre-push .githooks/commit-msg
    chmod +x scripts/*.sh
    git config core.hooksPath .githooks
    mkdir -p .tools
    git add -A
    # --no-verify: skip gates on scaffold seed commit (no real code, tools not installed).
    git -c commit.gpgsign=false commit -q --no-verify -m "init: scaffold bootstrap"
  )
}

# Snapshot the BASE_SHA in a repo. Call once after bootstrap.
snapshot_base() {
  ( cd "$1" && git rev-parse HEAD )
}

# Reset working tree + gate runtime state. Call at start of each scenario.
# Args: <repo_dir> <base_sha>
reset_state() {
  local repo="$1" base="$2"
  ( cd "$repo"
    git reset --hard "$base" >/dev/null 2>&1
    git clean -fdx >/dev/null 2>&1
    rm -f .git/gates-last-run .git/gates-perf.log .git/gates.lock
  )
  unset GATES_SKIP GATES_DRY_RUN GATES_LOCK_STALE_S 2>/dev/null || true
  export PATH="$ORIG_PATH"
}

# Run <fn> inside <repo>, with reset_state first.
# Args: <repo> <base_sha> <fn_name>
with_repo() {
  local repo="$1" base="$2" fn="$3"
  reset_state "$repo" "$base"
  ( cd "$repo" && "$fn" )
}

# Install a stub tool that exits with the given code and emits optional stdout.
# Args: <tool_name> <exit_code> [stdout_msg]
install_stub_tool() {
  local name="$1" rc="$2" msg="${3:-}"
  local dir="$UAT_ROOT/stubs/${name}_${rc}"
  mkdir -p "$dir"
  cat >"$dir/$name" <<EOF
#!/usr/bin/env bash
[ -n "$msg" ] && echo "$msg"
exit $rc
EOF
  chmod +x "$dir/$name"
  export PATH="$dir:$PATH"
}

# Strip all stubs from PATH (used by reset_state via ORIG_PATH).
restore_real_tool() {
  export PATH="$ORIG_PATH"
}

# Write a stub tool directly into <repo>/.tools/<name>.
# Used for gates that resolve the tool via .tools/<name> (not PATH).
# Args: <repo_dir> <tool_name> <exit_code> [stdout_msg]
install_repo_tool() {
  local repo="$1" name="$2" rc="$3" msg="${4:-}"
  mkdir -p "$repo/.tools"
  cat >"$repo/.tools/$name" <<EOF
#!/usr/bin/env bash
[ -n "$msg" ] && echo "$msg"
exit $rc
EOF
  chmod +x "$repo/.tools/$name"
}

# === Scenarios (filled in Task 4-11) ===================================

# === Bootstrap group ===================================================

s01_bootstrap_fresh() {
  # bootstrap.sh wires hooks in an already-scaffolded repo; it does not create
  # the scaffold files itself. Use bootstrap_test_repo to lay down the template,
  # then run bootstrap.sh to wire the hooks, and assert wiring held.
  local repo="$UAT_ROOT/repos/bootstrap_fresh"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  cd "$repo"
  "$SCAFFOLD_ROOT/skills/scaffold-with-guardrails/templates/common/scripts/bootstrap.sh" --offline
  assert_file_exists .githooks/pre-commit || return 1
  assert_file_exists .gates.toml          || return 1
  assert_file_exists .tools               || return 1
  local hp; hp="$(git config core.hooksPath)"
  [ "$hp" = ".githooks" ] || { echo "core.hooksPath=$hp"; return 1; }
}

s02_bootstrap_idempotent() {
  # bootstrap.sh does not emit an idempotency message; it reruns all 7 steps
  # each invocation. Idempotency is structural: step 5 skips adding include.path
  # if already present. Assert: second run exits 0 AND include.path is not
  # duplicated in git config.
  local repo="$UAT_ROOT/repos/bootstrap_idempotent"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  cd "$repo"
  local bs="$SCAFFOLD_ROOT/skills/scaffold-with-guardrails/templates/common/scripts/bootstrap.sh"
  "$bs" --offline >/dev/null 2>&1
  local out rc
  out=$("$bs" --offline 2>&1)
  rc=$?
  assert_exit 0 "$rc" || return 1
  # include.path must appear exactly once (idempotent step 5).
  local count
  count=$(git config --get-all include.path 2>/dev/null | grep -c '^\.\./\.gitconfig\.gates$' || true)
  [ "$count" -le 1 ] || { echo "ASSERT FAIL: include.path duplicated (count=$count)"; return 1; }
}

s03_bootstrap_offline() {
  # Verify that --offline exits 0 and does not download any tool binaries.
  # scaffold files are laid down by bootstrap_test_repo; bootstrap.sh is then
  # run to confirm --offline skips the fetch steps without error.
  local repo="$UAT_ROOT/repos/bootstrap_offline"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  cd "$repo"
  local out rc
  out=$("$SCAFFOLD_ROOT/skills/scaffold-with-guardrails/templates/common/scripts/bootstrap.sh" --offline 2>&1)
  rc=$?
  assert_exit 0 "$rc" || return 1
  assert_file_exists .githooks/pre-commit || return 1
  # --offline must NOT have downloaded tool binaries (only .gitkeep is allowed).
  if find .tools -type f ! -name '.gitkeep' 2>/dev/null | grep -q .; then
    echo "ASSERT FAIL: --offline downloaded tools" >&2
    return 1
  fi
}

s04_worktree() {
  local main="$UAT_ROOT/repos/bootstrap_worktree_main"
  local wt="$UAT_ROOT/repos/bootstrap_worktree_wt"
  rm -rf "$main" "$wt"
  bootstrap_test_repo "$main"
  ( cd "$main" && git worktree add "$wt" -b uat-branch )
  # Hook must resolve REPO_ROOT correctly from the worktree.
  ( cd "$wt"
    echo "x=1" > test.py
    git add test.py
    local out rc
    out=$(.githooks/pre-commit 2>&1); rc=$?
    # Exit 0 (no violations) or 1 (some gate fired) — either is acceptable.
    # What we test is: hook executed without "REPO_ROOT not found" / path errors.
    if echo "$out" | grep -qE 'REPO_ROOT.*not.*found|cannot find|No such file'; then
      echo "ASSERT FAIL: worktree path resolution broken"; echo "$out"; return 1
    fi
  ) || return 1
}

s05_verify_tool_pins() {
  # verify-tool-pins.sh defaults to .tools/manifest.toml.
  # The template ships manifest.toml.template (with REPLACE_ME placeholders);
  # copy it to .tools/manifest.toml so the script finds it.
  local repo="$UAT_ROOT/repos/bootstrap_pins"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  cd "$repo"
  cp "$SCAFFOLD_ROOT/skills/scaffold-with-guardrails/templates/common/tools/manifest.toml.template" \
     .tools/manifest.toml
  # Manifest ships with REPLACE_ME placeholders; bootstrap normally fills them.
  # Run verify-tool-pins.sh against unfilled manifest.
  local out rc
  out=$(./scripts/verify-tool-pins.sh 2>&1); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "REPLACE_ME|unpinned|stale" "$out" || return 1
}

# === Gates-fire group ==================================================

s06_format() {
  # ruff format gate (10-format) fires when pyproject.toml has [tool.ruff] and
  # a ruff stub exits 1 (unformatted output detected).
  local repo="$UAT_ROOT/repos/gates_format"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  # Trigger has_ruff_format detector.
  printf '[tool.ruff]\n' >> "$repo/pyproject.toml"
  # Staged .py file so the hook has something to commit.
  printf 'x = 1\n' > "$repo/main.py"
  ( cd "$repo" && git add pyproject.toml main.py )
  # Stub ruff exits 1 → unformatted.
  install_stub_tool ruff 1 "Would reformat main.py"
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "10-format|ruff" "$out" || return 1
}

s07_secrets() {
  # gitleaks gate (20-secrets) fires when .tools/gitleaks exits 1 (secret found).
  # Gate resolves the tool via .tools/gitleaks directly — PATH stub is insufficient.
  local repo="$UAT_ROOT/repos/gates_secrets"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  install_repo_tool "$repo" gitleaks 1 "secret found"
  # Stage a file so the hook has something to commit.
  printf 'API_KEY=hunter2\n' > "$repo/config.txt"
  ( cd "$repo" && git add config.txt )
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "20-secrets|gitleaks" "$out" || return 1
}

s08_static_analysis() {
  # semgrep gate (30-static-analysis) fires when a staged .py file is found and
  # the semgrep stub exits 1 (findings). Gate falls back to PATH when .tools/semgrep
  # is absent, so install_stub_tool is sufficient here.
  local repo="$UAT_ROOT/repos/gates_static"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  # Create a minimal .semgrep config dir (gate passes --config .semgrep to the tool).
  mkdir -p "$repo/.semgrep"
  printf 'rules: []\n' > "$repo/.semgrep/rules.yaml"
  # Stage a .py file so the self-skip check passes.
  printf 'import os\n' > "$repo/app.py"
  ( cd "$repo" && git add app.py .semgrep/ )
  # Stub semgrep exits 1 → findings (not tool error).
  install_stub_tool semgrep 1 "found 1 finding"
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "30-static-analysis|semgrep" "$out" || return 1
}

s09_deps() {
  # trivy gate (40-deps) fires when a staged manifest is found and .tools/trivy
  # exits 1 (HIGH/CRITICAL findings). Gate resolves the tool via .tools/trivy.
  local repo="$UAT_ROOT/repos/gates_deps"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  install_repo_tool "$repo" trivy 1 "HIGH vulnerability found"
  # Stage package.json to satisfy the manifest pattern check.
  printf '{"name":"test","version":"1.0.0"}\n' > "$repo/package.json"
  ( cd "$repo" && git add package.json )
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "40-deps|trivy" "$out" || return 1
}

s10_tests_unit() {
  # pytest gate (50-tests-unit) fires when pyproject.toml + tests/ dir exist and
  # the pytest stub exits 1 (failing tests). Exit 5 = no tests collected → self-skip;
  # we use exit 1 to ensure the gate blocks.
  local repo="$UAT_ROOT/repos/gates_tests"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  # Satisfy has_python_tests: needs pyproject.toml + tests/ dir.
  printf '[build-system]\nrequires = []\n' > "$repo/pyproject.toml"
  mkdir -p "$repo/tests"
  # Stage at least one file so pre-commit has a reason to run.
  printf 'def add(a, b): return a + b\n' > "$repo/lib.py"
  ( cd "$repo" && git add pyproject.toml lib.py && git add tests/ 2>/dev/null || true )
  # Stub pytest exits 1 → test failures (not "no tests collected").
  install_stub_tool pytest 1 "FAILED tests/test_lib.py::test_add"
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "50-tests-unit|pytest" "$out" || return 1
}

s11_complexity_standard_warn() {
  # 60-complexity is optional tier → warns (not blocks) under standard profile.
  # lizard stub exits 1 (findings). Gate emits gate_warn_block but exits 0.
  # Verify: pre-commit exits 0 and FAILED= line in gates-last-run is empty.
  # Bystander gates that would otherwise block (gitleaks/semgrep/scc MISSING) get
  # passing repo-tool stubs so the isolation target is complexity alone.
  local repo="$UAT_ROOT/repos/gates_complexity"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"   # default profile = standard
  # Install the gate under test: lizard exits 1 (findings → warn in standard).
  install_repo_tool "$repo" lizard 1 "function complexity exceeds threshold"
  # Bystander stubs (exit 0 = pass) so other gates don't block the commit.
  install_repo_tool "$repo" gitleaks 0
  install_repo_tool "$repo" semgrep 0
  install_repo_tool "$repo" scc 0 "[]"  # scc outputs JSON; empty array = no files
  # Stage a .py file to pass the self-skip check (complexity, static-analysis, file-size).
  printf 'def f(): pass\n' > "$repo/module.py"
  ( cd "$repo" && git add module.py )
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 0 "$rc" || return 1
  assert_output_contains "WARN|60-complexity" "$out" || return 1
  # gates-last-run must exist and FAILED= must be empty (no blocking failures).
  assert_file_exists "$repo/.git/gates-last-run" || return 1
  local failed_line
  failed_line=$(grep '^FAILED=' "$repo/.git/gates-last-run")
  if [ "$failed_line" != "FAILED=" ]; then
    echo "ASSERT FAIL: expected empty FAILED= in gates-last-run, got: $failed_line" >&2
    return 1
  fi
}

s12_complexity_regulated_fail() {
  # 60-complexity is optional tier → error (not warn) under regulated profile.
  # lizard exits 1 (findings); gate must exit 1 (blocking failure).
  local repo="$UAT_ROOT/repos/gates_complexity_regulated"
  rm -rf "$repo"
  bootstrap_test_repo "$repo" regulated
  # Gate under test: lizard exits 1 (findings → error in regulated).
  install_repo_tool "$repo" lizard 1 "function complexity exceeds threshold"
  # Bystander stubs (exit 0 = pass) isolate the complexity gate.
  install_repo_tool "$repo" gitleaks 0
  install_repo_tool "$repo" semgrep  0
  install_repo_tool "$repo" scc      0
  install_repo_tool "$repo" trivy    0
  # Stage a .py file to satisfy the self-skip check.
  printf 'def f(): pass\n' > "$repo/module.py"
  ( cd "$repo" && git add module.py )
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "60-complexity|lizard" "$out" || return 1
}

s13_file_size() {
  # 61-file-size is optional tier → warn (not block) under standard profile.
  # scc stub emits JSON reporting a file with 9999 LOC (> default max 400).
  # Gate emits WARN but pre-commit exits 0.
  local repo="$UAT_ROOT/repos/gates_file_size"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"   # default profile = standard
  # Custom scc stub: emits JSON with a violating file before exiting 0.
  mkdir -p "$repo/.tools"
  cat > "$repo/.tools/scc" <<'STUB'
#!/usr/bin/env bash
cat <<'JSON'
[{"Files":[{"Location":"big.py","Code":9999}]}]
JSON
exit 0
STUB
  chmod +x "$repo/.tools/scc"
  # Bystander stubs so other gates don't block.
  install_repo_tool "$repo" gitleaks 0
  install_repo_tool "$repo" semgrep  0
  install_repo_tool "$repo" lizard   0
  # Stage a .py file to satisfy staged-source self-skip checks.
  printf 'def f(): pass\n' > "$repo/big.py"
  ( cd "$repo" && git add big.py )
  local out rc
  out=$( cd "$repo" && .githooks/pre-commit 2>&1 ); rc=$?
  assert_exit 0 "$rc" || return 1
  assert_output_contains "61-file-size|WARN" "$out" || return 1
}

s14_tests_integration() {
  # 10-tests-integration is a pre-push gate (critical tier).
  # has_python_integration: needs pyproject.toml + tests/ directory.
  # pytest stub exits 1 (failing tests, not 5 = "no tests") → gate exits 1.
  local repo="$UAT_ROOT/repos/gates_tests_integration"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  # Satisfy has_python_integration: needs pyproject.toml + tests/ dir.
  printf '[build-system]\nrequires = []\n' > "$repo/pyproject.toml"
  mkdir -p "$repo/tests"
  ( cd "$repo" && git add pyproject.toml && git add tests/ 2>/dev/null || true )
  # Stub pytest exits 1 → test failures (not "no tests collected").
  install_stub_tool pytest 1 "FAILED tests/test_integration.py::test_api"
  # Invoke pre-push directly (no stdin needed — dispatcher does not read it).
  local out rc
  out=$( cd "$repo" && .githooks/pre-push </dev/null 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "10-tests-integration|pytest" "$out" || return 1
}

s15_deps_deep() {
  # 20-deps-deep is a pre-push gate (critical tier).
  # trivy resolved via .tools/trivy; exits 1 (HIGH/CRITICAL findings) → gate exits 1.
  local repo="$UAT_ROOT/repos/gates_deps_deep"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  install_repo_tool "$repo" trivy 1 "HIGH vulnerability found"
  local out rc
  out=$( cd "$repo" && .githooks/pre-push </dev/null 2>&1 ); rc=$?
  assert_exit 1 "$rc" || return 1
  assert_output_contains "20-deps-deep|trivy" "$out" || return 1
}

s16_conventional_commit() {
  # SPEC DEVIATION: 10-conventional is warn-only — it always exits 0 (see gate line 18).
  # The gate emits a WARN for non-conventional subjects but never blocks the commit.
  # We test the WARN behavior: a bad subject → WARN in output, commit succeeds (exit 0).
  #
  # Strategy to isolate commit-msg gate:
  #   - Stage only a non-.py file (README.md) so pre-commit's source-gated gates
  #     self-skip (format/static-analysis/complexity/file-size need staged .py files).
  #   - Install passing bystander repo-tool stubs for gitleaks + trivy (pre-commit scans).
  #   - pre-commit exits 0 → commit proceeds to commit-msg hook.
  local repo="$UAT_ROOT/repos/gates_conventional"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"
  # Bystander stubs: gates that fire regardless of file type.
  install_repo_tool "$repo" gitleaks 0
  install_repo_tool "$repo" trivy    0
  # Stage a non-.py file to avoid triggering source-gated checks.
  printf '# project\n' > "$repo/README.md"
  ( cd "$repo" && git add README.md )
  # Commit with a non-conventional subject; capture combined output.
  # commit.gpgsign=false avoids GPG prompts in CI.
  local out rc
  out=$( cd "$repo" && git -c commit.gpgsign=false commit -m "wip messing around" 2>&1 ); rc=$?
  assert_exit 0 "$rc" || return 1
  assert_output_contains "conventional|WARN" "$out" || return 1
}

# === Trailer group =====================================================

s17_trailer_yes() {
  # Verified: yes — every gate runs and passes; SKIPPED and FAILED both empty.
  #
  # Gates that fire and their trigger conditions:
  #   10-format      : pyproject.toml with [tool.ruff] → PATH stub ruff exits 0
  #   20-secrets     : always → .tools/gitleaks exits 0
  #   30-static-analysis : staged .py file → .tools/semgrep exits 0
  #   40-deps        : staged pyproject.toml (manifest) → .tools/trivy exits 0
  #   50-tests-unit  : pyproject.toml + tests/ dir → PATH stub pytest exits 0
  #   60-complexity  : staged .py file → .tools/lizard exits 0
  #   61-file-size   : staged .py file → .tools/scc emits empty JSON [] exits 0
  # None must self-skip (exit 77), so all stack detectors must see their preconditions.
  local repo="$UAT_ROOT/repos/trailer_yes"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"

  # pyproject.toml: satisfies has_ruff_format (10-format) + has_python_tests (50-tests-unit)
  # + 40-deps manifest detector. Needs [tool.ruff] section AND [build-system] or similar.
  printf '[tool.ruff]\n\n[build-system]\nrequires = []\n' > "$repo/pyproject.toml"

  # tests/ dir: satisfies has_python_tests so 50-tests-unit fires instead of self-skipping.
  mkdir -p "$repo/tests"

  # .semgrep dir: 30-static-analysis passes --config .semgrep; stub ignores args but dir
  # is created here for fidelity. Gate does not require the dir to exist; stub handles it.
  mkdir -p "$repo/.semgrep"

  # Stage .py file (triggers 30-static-analysis, 60-complexity, 61-file-size)
  # and pyproject.toml (triggers 40-deps via manifest detection).
  printf 'def hello(): pass\n' > "$repo/app.py"
  ( cd "$repo" && git add pyproject.toml app.py ) || return 1

  # PATH stubs (tools resolved via PATH).
  install_stub_tool ruff   0
  install_stub_tool pytest 0

  # Repo-tool stubs (tools resolved via .tools/<name>).
  install_repo_tool "$repo" gitleaks 0
  install_repo_tool "$repo" semgrep  0
  install_repo_tool "$repo" trivy    0
  install_repo_tool "$repo" lizard   0

  # scc is special: 61-file-size parses JSON output. Empty array → no violators → pass.
  cat > "$repo/.tools/scc" <<'STUB'
#!/usr/bin/env bash
echo '[]'
exit 0
STUB
  chmod +x "$repo/.tools/scc"

  # Commit with a conventional subject so 10-conventional (commit-msg gate) stays quiet.
  local out rc
  out=$( cd "$repo" && git -c commit.gpgsign=false commit -m "feat: trailer test" 2>&1 ); rc=$?
  assert_exit 0 "$rc" || return 1
  ( cd "$repo" && assert_trailer "yes" ) || return 1
}

s18_trailer_no() {
  # Verified: no — --no-verify skips ALL hooks (pre-commit AND commit-msg).
  # The 20-verified-trailer gate in commit-msg never runs → no trailer appended.
  local repo="$UAT_ROOT/repos/trailer_no"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"

  printf 'placeholder\n' > "$repo/README.md"
  ( cd "$repo" && git add README.md ) || return 1

  git -C "$repo" -c commit.gpgsign=false commit --no-verify -m "feat: bypass" >/dev/null 2>&1
  ( cd "$repo" && assert_no_trailer ) || return 1
}

s19_trailer_partial() {
  # Verified: partial — pre-commit runs, at least one gate ends up in SKIPPED,
  # zero gates in FAILED.
  #
  # Strategy: stage a .py file so source-gated gates fire (not self-skip).
  # Force 20-secrets into SKIPPED via GATES_SKIP=secrets.
  # Install passing stubs for every other gate that will fire so none fail.
  local repo="$UAT_ROOT/repos/trailer_partial"
  rm -rf "$repo"
  bootstrap_test_repo "$repo"

  # pyproject.toml with [tool.ruff]: triggers 10-format (ruff stub) + 40-deps (trivy stub).
  printf '[tool.ruff]\n\n[build-system]\nrequires = []\n' > "$repo/pyproject.toml"

  # tests/ dir: triggers 50-tests-unit (pytest stub).
  mkdir -p "$repo/tests"

  # Stage .py + pyproject.toml.
  printf 'def hello(): pass\n' > "$repo/app.py"
  ( cd "$repo" && git add pyproject.toml app.py ) || return 1

  # PATH stubs.
  install_stub_tool ruff   0
  install_stub_tool pytest 0

  # Repo-tool stubs (gitleaks skipped via GATES_SKIP, but stub present for safety).
  install_repo_tool "$repo" gitleaks 0
  install_repo_tool "$repo" semgrep  0
  install_repo_tool "$repo" trivy    0
  install_repo_tool "$repo" lizard   0

  # scc: must emit valid JSON so 61-file-size parses cleanly.
  cat > "$repo/.tools/scc" <<'STUB'
#!/usr/bin/env bash
echo '[]'
exit 0
STUB
  chmod +x "$repo/.tools/scc"

  # GATES_SKIP=secrets forces 20-secrets into SKIPPED → trailer becomes "partial".
  local out rc
  out=$( cd "$repo" && GATES_SKIP=secrets git -c commit.gpgsign=false commit -m "feat: partial test" 2>&1 ); rc=$?
  assert_exit 0 "$rc" || return 1
  ( cd "$repo" && assert_trailer "partial" ) || return 1
}

# === Driver ============================================================
SCENARIOS=(
  s01_bootstrap_fresh
  s02_bootstrap_idempotent
  s03_bootstrap_offline
  s04_worktree
  s05_verify_tool_pins
  s06_format
  s07_secrets
  s08_static_analysis
  s09_deps
  s10_tests_unit
  s11_complexity_standard_warn
  s12_complexity_regulated_fail
  s13_file_size
  s14_tests_integration
  s15_deps_deep
  s16_conventional_commit
  s17_trailer_yes
  s18_trailer_no
  s19_trailer_partial
)

cleanup() {
  if [ "${#FAILED[@]}" -eq 0 ]; then
    rm -rf "$UAT_ROOT"
  else
    echo ""
    echo "Diagnostic dir: $UAT_ROOT"
    echo "Failed scenarios: ${FAILED[*]}"
    echo "Per-scenario logs: $UAT_ROOT/logs/"
  fi
}
trap cleanup EXIT

print_summary() {
  echo ""
  echo "==========================="
  echo "PASS: ${#PASSED[@]}"
  echo "FAIL: ${#FAILED[@]}"
  if [ "${#FAILED[@]}" -gt 0 ]; then
    echo "FAILED: ${FAILED[*]}"
  fi
  echo "==========================="
}

record_pass() { PASSED+=("$1"); }
record_fail() { FAILED+=("$1"); }

main() {
  local scenarios_to_run=()
  if [ -n "$ONLY" ]; then
    scenarios_to_run=("$ONLY")
  else
    scenarios_to_run=("${SCENARIOS[@]}")
  fi

  for s in "${scenarios_to_run[@]}"; do
    printf "==> %s\n" "$s"
    local log="$UAT_ROOT/logs/${s}.log"
    if "$s" >"$log" 2>&1; then
      record_pass "$s"
    else
      record_fail "$s"
      [ "$VERBOSE" -eq 1 ] && cat "$log"
    fi
  done

  print_summary
  [ "${#FAILED[@]}" -eq 0 ]
}

# Skip main if no scenarios (skeleton mode).
if [ "${#SCENARIOS[@]}" -eq 0 ] && [ -z "$ONLY" ]; then
  echo "(skeleton mode — no scenarios registered)"
  print_summary
  exit 0
fi

main
