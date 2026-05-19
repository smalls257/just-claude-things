#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "10-format self-skips when no formatter applicable" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  echo "x" > README.md
  git add README.md
  run git commit -m "test"
  assert_output --partial "SKIP: 10-format (self-skip)"
  refute_output --partial "[FAIL 10-format]"
}

@test "10-format blocks on dotnet format diff" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "dotnet" 1 "src/Foo.cs(1,1): error WHITESPACE: needs format"
  export PATH="$REPO/.tools:$PATH"
  echo '<Project Sdk="Microsoft.NET.Sdk"/>' > App.csproj
  mkdir -p src
  echo "class Foo {}" > src/Foo.cs
  git add App.csproj src/Foo.cs
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 10-format]"
}

@test "10-format blocks with MISSING when dotnet absent and .NET stack present" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  # Build a PATH that contains git and standard utils but excludes any dotnet installation.
  # We locate git explicitly so the commit still works, then strip dotnet from the path.
  local git_dir
  git_dir="$(dirname "$(command -v git)")"
  # Construct a minimal PATH: standard POSIX dirs + git's dir, no dotnet.
  local dotnet_dir
  dotnet_dir="$(dirname "$(command -v dotnet 2>/dev/null || echo /nonexistent/dotnet)")"
  # Build PATH from known-good components, excluding dotnet's directory.
  local new_path="/usr/bin:/bin:/usr/sbin:/sbin"
  if [ "$git_dir" != "/usr/bin" ] && [ "$git_dir" != "/bin" ]; then
    new_path="${new_path}:${git_dir}"
  fi
  export PATH="$new_path"
  # Hard-verify dotnet is off PATH before driving the test. Avoids silent false-passes
  # if a future build env has dotnet outside our strip set.
  if command -v dotnet >/dev/null 2>&1; then
    skip "dotnet is still on PATH in this environment; cannot test MISSING path here"
  fi
  echo '<Project Sdk="Microsoft.NET.Sdk"/>' > App.csproj
  git add App.csproj
  run git commit -m "test"
  assert_failure
  assert_output --partial "[MISSING 10-format]"
}
