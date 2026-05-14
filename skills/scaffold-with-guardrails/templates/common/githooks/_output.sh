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
}

gate_missing_tool() {
  local gate="$1"; local tool="$2"; local hint="$3"
  echo "[MISSING ${gate}] ${tool} not found" >&2
  echo "" >&2
  echo "  ${hint}" >&2
  echo "" >&2
  echo "  Run: ./scripts/bootstrap.sh" >&2
  return 2
}

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
