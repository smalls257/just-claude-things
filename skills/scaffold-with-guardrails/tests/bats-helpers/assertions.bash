# Custom assertions for gate tests.
# Wraps bats-support and bats-assert with gate-specific helpers.

# shellcheck disable=SC2154
_BATS_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
load "${_BATS_HELPERS_DIR}/../_bats-support/load.bash"
load "${_BATS_HELPERS_DIR}/../_bats-assert/load.bash"

assert_gate_blocked() {
  local gate="$1"
  assert_output --partial "[FAIL ${gate}]"
}

assert_verified_trailer() {
  local value="$1"   # yes | no | partial
  local sha="${2:-HEAD}"
  local msg
  msg="$(git -C "$REPO" log -1 --format=%B "$sha")"
  if ! grep -q "Verified: ${value}" <<<"$msg"; then
    echo "expected 'Verified: ${value}' in commit message; got:" >&2
    echo "$msg" >&2
    return 1
  fi
}

# --- Task lifecycle assertions (Phase-1.5) ---

assert_task_completed() {
  local log="$1"
  local name="$2"
  grep -q "TASK\[$name\] status=completed" "$log" \
    || { echo "TASK_NOT_COMPLETED: $name (log: $log)" >&2; return 1; }
}

assert_task_in_progress() {
  local log="$1"
  local name="$2"
  grep -q "TASK\[$name\] status=in_progress" "$log" \
    || { echo "TASK_NOT_IN_PROGRESS: $name (log: $log)" >&2; return 1; }
}
