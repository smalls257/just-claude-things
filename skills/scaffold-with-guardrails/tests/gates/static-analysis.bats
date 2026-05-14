#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "30-static-analysis runs semgrep with metrics off" {
  cd "$REPO"
  # Wrap semgrep to record env it sees — write to per-test log inside $REPO
  cat > "$REPO/.tools/semgrep" <<'EOF'
#!/usr/bin/env bash
echo "SEMGREP_SEND_METRICS=${SEMGREP_SEND_METRICS:-unset}" >> "$(dirname "$0")/../.env-log"
exit 0
EOF
  chmod +x "$REPO/.tools/semgrep"
  install_stub_tool "gitleaks" 0
  : > "$REPO/.env-log"
  echo "foo" > a.cs
  git add a.cs
  git commit -m "test"
  run cat "$REPO/.env-log"
  assert_output --partial "SEMGREP_SEND_METRICS=off"
}

@test "30-static-analysis self-skips when no source files in scan paths" {
  cd "$REPO"
  install_stub_tool "semgrep" 0
  # Only README, no .cs/.py/.ts files
  echo "x" > NOTES.md
  git add NOTES.md
  run git commit -m "test"
  refute_output --partial "[FAIL 30-static-analysis]"
}

@test "30-static-analysis blocks on findings" {
  cd "$REPO"
  install_stub_tool "semgrep" 1 "src/foo.cs:10: bookworm-no-empty-catch"
  mkdir -p src
  echo "x" > src/foo.cs
  git add src/foo.cs
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 30-static-analysis]"
}
