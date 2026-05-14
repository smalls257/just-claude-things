#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "50-tests-unit blocks on test failure" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "dotnet" 1 "Failed: 1, Passed: 0"
  export PATH="$REPO/.tools:$PATH"
  # Create a tests/<proj>/<proj>.Tests.Unit.csproj that the bounded find detects.
  mkdir -p tests/App.Tests.Unit
  echo '<Project Sdk="Microsoft.NET.Sdk"/>' > tests/App.Tests.Unit/App.Tests.Unit.csproj
  git add tests/App.Tests.Unit/App.Tests.Unit.csproj
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 50-tests-unit]"
}

@test "50-tests-unit self-skips when no test project" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  echo "x" > README.md
  git add README.md
  run git commit -m "test"
  assert_output --partial "SKIP: 50-tests-unit (self-skip)"
  refute_output --partial "[FAIL 50-tests-unit]"
}

@test "50-tests-unit reports MISSING when dotnet absent and unit tests present" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  # Strip dotnet from PATH defensively (same pattern as T11 test 3)
  local git_dir; git_dir="$(dirname "$(command -v git)")"
  export PATH="/usr/bin:/bin:$git_dir"
  if command -v dotnet >/dev/null 2>&1; then
    skip "dotnet still on PATH; cannot test MISSING path here"
  fi
  mkdir -p tests/App.Tests.Unit
  echo '<Project Sdk="Microsoft.NET.Sdk"/>' > tests/App.Tests.Unit/App.Tests.Unit.csproj
  git add tests/App.Tests.Unit/App.Tests.Unit.csproj
  run git commit -m "test"
  assert_failure
  assert_output --partial "[MISSING 50-tests-unit]"
}
