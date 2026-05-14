#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "pre-push --self-test reachable" {
  cd "$REPO"
  run "$REPO/.githooks/pre-push" --self-test
  assert_success
  assert_output --partial "pre-push dispatcher reachable"
}

@test "pre-push runs 20-deps-deep and reports MISSING when trivy absent" {
  cd "$REPO"
  rm -f "$REPO/.tools/trivy"
  # Strip trivy from PATH defensively.
  local git_dir; git_dir="$(dirname "$(command -v git)")"
  export PATH="/usr/bin:/bin:$git_dir"
  if command -v trivy >/dev/null 2>&1; then
    skip "trivy still on PATH; cannot test MISSING path here"
  fi
  run "$REPO/.githooks/pre-push"
  assert_failure
  assert_output --partial "[MISSING 20-deps-deep]"
}
