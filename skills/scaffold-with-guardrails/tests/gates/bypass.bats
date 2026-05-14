#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "GATES_DRY_RUN=1 runs gates but never blocks" {
  cd "$REPO"
  rm -rf .githooks/pre-commit.d/*
  cat > .githooks/pre-commit.d/20-fail <<'EOF'
#!/usr/bin/env bash
echo "would fail"
exit 1
EOF
  chmod +x .githooks/pre-commit.d/20-fail
  echo "x" > a.txt
  git add a.txt
  GATES_DRY_RUN=1 run git commit -m "test"
  assert_success
  assert_output --partial "DRY: would run 20-fail"
}

@test "concurrent commit blocked by lock" {
  cd "$REPO"
  rm -rf .githooks/pre-commit.d/*
  cat > .githooks/pre-commit.d/10-slow <<'EOF'
#!/usr/bin/env bash
sleep 1
exit 0
EOF
  chmod +x .githooks/pre-commit.d/10-slow
  echo "a" > a.txt; git add a.txt
  echo "b" > b.txt
  # Start first commit in background; it will hold the lock for ~1s.
  ( git commit -m "a" ) &
  pid=$!
  # 0.3s headroom: long enough for A's hook to acquire lock,
  # short enough to land well before A's 1s gate finishes.
  sleep 0.3
  # Stage distinct content for B so it doesn't race A on the same index entry.
  git add b.txt
  run git commit -m "b"
  assert_failure
  assert_output --partial "Another gate run is in progress"
  wait "$pid"
}

@test "pre-push --no-verify logs to .git/gates.log" {
  skip "manual smoke -- requires remote"
}
