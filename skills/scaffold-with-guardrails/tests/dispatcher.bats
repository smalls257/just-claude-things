#!/usr/bin/env bats
load 'bats-helpers/fixtures'
load 'bats-helpers/assertions'

setup() {
  new_repo
  install_gates_template
  rm -rf "$REPO/.githooks/pre-commit.d"
  mkdir -p "$REPO/.githooks/pre-commit.d"
  cat > "$REPO/.githooks/pre-commit.d/10-pass" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  cat > "$REPO/.githooks/pre-commit.d/20-fail" <<'EOF'
#!/usr/bin/env bash
echo "boom" >&2
exit 1
EOF
  chmod +x "$REPO/.githooks/pre-commit.d/"*
}
teardown() { cleanup_repo; }

@test "dispatcher runs all gates in numeric order" {
  echo "x" > "$REPO/file.txt"
  git -C "$REPO" add file.txt
  run git -C "$REPO" commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 20-fail]"
}

@test "dispatcher returns 0 when all gates pass" {
  rm "$REPO/.githooks/pre-commit.d/20-fail"
  echo "x" > "$REPO/file.txt"
  git -C "$REPO" add file.txt
  run git -C "$REPO" commit -m "test"
  assert_success
}

@test "dispatcher honors GATES_SKIP" {
  echo "x" > "$REPO/file.txt"
  git -C "$REPO" add file.txt
  GATES_SKIP="fail" run git -C "$REPO" commit -m "test"
  assert_success
  assert_output --partial "SKIP: 20-fail"
}

@test "dispatcher treats exit 77 as self-skip, continues" {
  cat > "$REPO/.githooks/pre-commit.d/15-noop" <<'EOF'
#!/usr/bin/env bash
exit 77
EOF
  chmod +x "$REPO/.githooks/pre-commit.d/15-noop"
  rm "$REPO/.githooks/pre-commit.d/20-fail"
  echo "x" > "$REPO/file.txt"
  git -C "$REPO" add file.txt
  run git -C "$REPO" commit -m "test"
  assert_success
  assert_output --partial "SKIP: 15-noop (self-skip)"
}

@test "dispatcher emits perf log line per gate" {
  echo "x" > "$REPO/file.txt"
  git -C "$REPO" add file.txt
  GATES_SKIP="fail" run git -C "$REPO" commit -m "test"
  assert_success
  run cat "$REPO/.git/gates-perf.log"
  assert_output --partial "pre-commit 10-pass"
}
