# shellcheck shell=bash
# Sourced by individual gate scripts for uniform output.

gate_fail() {
  local gate="$1"; local tool="$2"; shift 2
  echo "[FAIL ${gate}] ${tool}" >&2
  while [ $# -gt 0 ]; do
    echo "  $1" >&2
    shift
  done
  echo "" >&2
  return 1
}

# Like gate_fail but reads diagnostic lines from stdin (for piping linter output).
# Usage: some_linter | gate_fail_block "$gate" "$tool"
gate_fail_block() {
  local gate="$1"; local tool="$2"
  echo "[FAIL ${gate}] ${tool}" >&2
  while IFS= read -r line; do
    echo "  $line" >&2
  done
  echo "" >&2
  return 1
}

gate_missing_tool() {
  local gate="$1"; local tool="$2"; local hint="$3"
  echo "[MISSING ${gate}] ${tool} not found" >&2
  echo "" >&2
  echo "  ${hint}" >&2
  echo "" >&2
  echo "  Run: ${GATES_BOOTSTRAP_CMD:-./scripts/bootstrap.sh}" >&2
  return 2
}

# Convention: gate basenames are NN-name (e.g., 30-static-analysis).
# The glob ${var#[0-9]*-} strips the NN- prefix to recover "name" for GATES_SKIP=.
gate_tool_error() {
  local gate="$1"; local tool="$2"; local code="$3"; shift 3
  echo "[ERROR ${gate}] ${tool} crashed" >&2
  echo "  Exit: ${code}" >&2
  echo "  Stderr:" >&2
  while [ $# -gt 0 ]; do
    echo "    $1" >&2
    shift
  done
  echo "" >&2
  echo "  This is a gate-config bug, not your code." >&2
  echo "  Bypass (audited): GATES_SKIP=${gate#[0-9]*-} git commit" >&2
  return 3
}

# Warn-tier output. Does NOT fail the gate. Caller still controls exit code.
gate_warn() {
  local gate="$1"; local tool="$2"; shift 2
  echo "[WARN ${gate}] ${tool}" >&2
  while [ $# -gt 0 ]; do
    echo "  $1" >&2
    shift
  done
  echo "" >&2
}

# Like gate_warn but reads diagnostic lines from stdin.
gate_warn_block() {
  local gate="$1"; local tool="$2"
  echo "[WARN ${gate}] ${tool}" >&2
  while IFS= read -r line; do
    echo "  $line" >&2
  done
  echo "" >&2
}
