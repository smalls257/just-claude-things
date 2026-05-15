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

# === Scenarios (filled in Task 4-11) ===================================

# === Driver ============================================================
SCENARIOS=()

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
