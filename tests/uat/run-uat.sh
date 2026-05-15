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
