#!/usr/bin/env bats

load 'bats-helpers/fixtures'
load 'bats-helpers/assertions'

setup() { new_repo; }
teardown() { cleanup_repo; }

@test "fixture creates a working repo" {
  [ -d "$REPO/.git" ]
  run git -C "$REPO" log
  assert_failure   # no commits yet
}
