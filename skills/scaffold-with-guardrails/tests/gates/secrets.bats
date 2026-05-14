#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "20-secrets blocks when gitleaks reports a finding" {
  install_stub_tool "gitleaks" 1 "[FINDING] AWS key detected in config.env:1"
  cd "$REPO"
  echo "AWS_KEY=AKIAEXAMPLE" > config.env
  git add config.env
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 20-secrets]"
}

@test "20-secrets passes when gitleaks exits clean" {
  install_stub_tool "gitleaks" 0
  cd "$REPO"
  echo "hello" > README.md
  git add README.md
  run git commit -m "test"
  assert_success
  refute_output --partial "[FAIL 20-secrets]"
}

@test "20-secrets blocks with MISSING when gitleaks absent" {
  cd "$REPO"
  rm -f "$REPO/.tools/gitleaks"
  echo "hello" > README.md
  git add README.md
  run git commit -m "test"
  assert_failure
  assert_output --partial "[MISSING 20-secrets]"
}
