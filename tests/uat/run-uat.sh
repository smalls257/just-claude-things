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
  actual="${actual// /}"
  expected="${expected// /}"
  if [ "$actual" != "$expected" ]; then
    echo "ASSERT FAIL: trailer Verified expected='$expected' got='$actual'" >&2
    return 1
  fi
}

assert_no_trailer() {
  local actual
  actual="$(git log -1 --format='%(trailers:key=Verified,valueonly,separator=)')"
  actual="${actual// /}"
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
