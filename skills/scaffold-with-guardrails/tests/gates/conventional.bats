#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "10-conventional warns on non-conventional subject" {
  cd "$REPO"
  local msg_file; msg_file=$(mktemp)
  echo "random message" > "$msg_file"
  run bash -c "$REPO/.githooks/commit-msg '$msg_file' 2>&1"
  rm -f "$msg_file"
  assert_success
  assert_output --partial "[WARN 10-conventional]"
}

@test "10-conventional silent on valid feat(scope): subject" {
  cd "$REPO"
  local msg_file; msg_file=$(mktemp)
  echo "feat(foo): add bar" > "$msg_file"
  run bash -c "$REPO/.githooks/commit-msg '$msg_file' 2>&1"
  rm -f "$msg_file"
  assert_success
  refute_output --partial "[WARN 10-conventional]"
}

@test "10-conventional silent on breaking-change fix!: with no scope" {
  cd "$REPO"
  local msg_file; msg_file=$(mktemp)
  echo "fix!: breaking change" > "$msg_file"
  run bash -c "$REPO/.githooks/commit-msg '$msg_file' 2>&1"
  rm -f "$msg_file"
  assert_success
  refute_output --partial "[WARN 10-conventional]"
}

@test "10-conventional silent on chore: with no scope" {
  cd "$REPO"
  local msg_file; msg_file=$(mktemp)
  echo "chore: tidy" > "$msg_file"
  run bash -c "$REPO/.githooks/commit-msg '$msg_file' 2>&1"
  rm -f "$msg_file"
  assert_success
  refute_output --partial "[WARN 10-conventional]"
}
