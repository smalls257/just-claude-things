#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "40-deps self-skips when no manifests present" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "trivy" 0
  echo "x" > README.md
  git add README.md
  run git commit -m "test"
  # Positive assertion — gate must actually run and self-skip, not be silently absent.
  assert_output --partial "SKIP: 40-deps (self-skip)"
  refute_output --partial "[FAIL 40-deps]"
}

@test "40-deps blocks on HIGH severity findings" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  install_stub_tool "trivy" 1 "vulnerability: CVE-2024-XXXX (HIGH) in package foo@1.0.0"
  echo '{"dependencies": {"foo": "1.0.0"}}' > package.json
  git add package.json
  run git commit -m "test"
  assert_failure
  assert_output --partial "[FAIL 40-deps]"
}

@test "40-deps blocks with MISSING when trivy absent and manifest staged" {
  cd "$REPO"
  install_stub_tool "gitleaks" 0
  rm -f "$REPO/.tools/trivy"
  echo '{"dependencies": {"foo": "1.0.0"}}' > package.json
  git add package.json
  run git commit -m "test"
  assert_failure
  assert_output --partial "[MISSING 40-deps]"
}
