#!/usr/bin/env bats
load ../bats-helpers/assertions

setup() {
  TASKLOG=$(mktemp)
  export TASKLOG
}

teardown() {
  rm -f "$TASKLOG"
}

@test "assert_task_completed finds completed line" {
  echo "TASK[step-3] status=completed" >> "$TASKLOG"
  run assert_task_completed "$TASKLOG" "step-3"
  [ "$status" -eq 0 ]
}

@test "assert_task_completed fails when only in_progress logged" {
  echo "TASK[step-3] status=in_progress" >> "$TASKLOG"
  run assert_task_completed "$TASKLOG" "step-3"
  [ "$status" -ne 0 ]
}

@test "assert_task_in_progress finds in_progress line" {
  echo "TASK[step-7] status=in_progress" >> "$TASKLOG"
  run assert_task_in_progress "$TASKLOG" "step-7"
  [ "$status" -eq 0 ]
}
