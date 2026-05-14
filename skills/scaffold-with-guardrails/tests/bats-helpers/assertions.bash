# Custom assertions for gate tests.
# Wraps bats-support and bats-assert with gate-specific helpers.

# shellcheck disable=SC2154
load "${BATS_TEST_DIRNAME}/_bats-support/load.bash"
load "${BATS_TEST_DIRNAME}/_bats-assert/load.bash"

assert_gate_blocked() {
  local gate="$1"
  assert_output --partial "[FAIL ${gate}]"
}

assert_verified_trailer() {
  local value="$1"   # yes | no | partial
  local sha="${2:-HEAD}"
  run git -C "$REPO" log -1 --format=%B "$sha"
  assert_output --partial "Verified: ${value}"
}
