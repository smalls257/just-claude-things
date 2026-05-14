#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "60-complexity warns by default in standard profile" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "semgrep" 0
  install_stub_tool "scc" 0
  install_stub_tool "lizard" 1 "src/big.cs:10: function bigFunc CCN=15"
  mkdir -p src
  echo "x" > src/big.cs
  git add src/big.cs
  run git commit -m "test"
  assert_success
  assert_output --partial "[WARN 60-complexity]"
}

@test "60-complexity self-skips when no source files staged" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "lizard" 0
  echo "x" > README.md
  git add README.md
  run git commit -m "test"
  assert_success
  assert_output --partial "SKIP: 60-complexity (self-skip)"
  refute_output --partial "[WARN 60-complexity]"
  refute_output --partial "[FAIL 60-complexity]"
}

@test "60-complexity reports MISSING when lizard absent and source files staged" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  rm -f "$REPO/.tools/lizard"
  # Strip lizard from PATH defensively (same pattern as T11/T12)
  local git_dir; git_dir="$(dirname "$(command -v git)")"
  export PATH="/usr/bin:/bin:$git_dir"
  if command -v lizard >/dev/null 2>&1; then
    skip "lizard still on PATH; cannot test MISSING path here"
  fi
  mkdir -p src
  echo "x" > src/big.cs
  git add src/big.cs
  run git commit -m "test"
  assert_failure
  assert_output --partial "[MISSING 60-complexity]"
}

@test "60-complexity fails in regulated profile" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "semgrep" 0
  install_stub_tool "scc" 0
  install_stub_tool "lizard" 1 "src/big.cs:10: function bigFunc CCN=15"
  # Set profile=regulated via .gates.toml override
  cat > "$REPO/.gates.toml" <<'EOF'
profile = "regulated"
max_ccn = 10
max_nloc = 60
EOF
  mkdir -p src
  echo "x" > src/big.cs
  git add src/big.cs
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 60-complexity]"
}
