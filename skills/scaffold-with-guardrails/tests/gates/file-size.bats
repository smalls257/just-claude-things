#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "61-file-size warns by default in standard profile" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "semgrep" 0
  install_stub_tool "lizard" 0
  install_stub_tool "scc" 0 '[{"Files":[{"Location":"src/Huge.cs","Code":500}]}]'
  mkdir -p src
  echo "x" > src/Huge.cs
  git add src/Huge.cs
  run git commit -m "test"
  assert_success
  assert_output --partial "[WARN 61-file-size]"
}

@test "61-file-size self-skips when no source files staged" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "scc" 0
  echo "x" > README.md
  git add README.md
  run git commit -m "test"
  assert_success
  assert_output --partial "SKIP: 61-file-size (self-skip)"
  refute_output --partial "[WARN 61-file-size]"
  refute_output --partial "[FAIL 61-file-size]"
}

@test "61-file-size reports MISSING when scc absent and source files staged" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "semgrep" 0
  install_stub_tool "lizard" 0
  rm -f "$REPO/.tools/scc"
  # Strip scc from PATH defensively (same pattern as T11/T12/T14).
  local git_dir; git_dir="$(dirname "$(command -v git)")"
  export PATH="/usr/bin:/bin:$git_dir"
  if command -v scc >/dev/null 2>&1; then
    skip "scc still on PATH; cannot test MISSING path here"
  fi
  mkdir -p src
  echo "x" > src/Huge.cs
  git add src/Huge.cs
  run git commit -m "test"
  assert_failure
  assert_output --partial "[MISSING 61-file-size]"
}

@test "61-file-size fails in regulated profile" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "semgrep" 0
  install_stub_tool "lizard" 0
  install_stub_tool "scc" 0 '[{"Files":[{"Location":"src/Huge.cs","Code":500}]}]'
  # Set profile=regulated via .gates.toml override
  cat > "$REPO/.gates.toml" <<'EOF'
profile = "regulated"
max_file_loc = 400
EOF
  mkdir -p src
  echo "x" > src/Huge.cs
  git add src/Huge.cs
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 61-file-size]"
}
