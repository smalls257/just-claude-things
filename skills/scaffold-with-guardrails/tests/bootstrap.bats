#!/usr/bin/env bats
load 'bats-helpers/fixtures'
load 'bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "manifest.toml has all 5 required tools" {
  for tool in gitleaks semgrep trivy lizard scc; do
    run grep -E "^\[${tool}\]" "$REPO/.tools/manifest.toml"
    assert_success
  done
}

@test "tools/.gitignore ignores binaries but keeps manifest" {
  # Initialize a tracking ref so check-ignore works.
  git -C "$REPO" add .tools/.gitignore .tools/manifest.toml 2>/dev/null || true
  run git -C "$REPO" check-ignore -q .tools/manifest.toml
  assert_failure
  # Drop a fake binary; it must be ignored.
  : > "$REPO/.tools/gitleaks"
  run git -C "$REPO" check-ignore -q .tools/gitleaks
  assert_success
}

@test "verify-tool-pins.sh fails on REPLACE_ME" {
  run "$REPO/scripts/verify-tool-pins.sh" "$REPO/.tools/manifest.toml"
  assert_failure
  assert_output --partial "REPLACE_ME"
}

@test "verify-tool-pins.sh passes on populated manifest" {
  sed -i.bak 's/REPLACE_ME/abc123/g' "$REPO/.tools/manifest.toml"
  rm -f "$REPO/.tools/manifest.toml.bak"
  run "$REPO/scripts/verify-tool-pins.sh" "$REPO/.tools/manifest.toml"
  assert_success
  assert_output --partial "Manifest OK"
}

@test "verify-tool-pins.sh exits 2 when manifest missing" {
  run "$REPO/scripts/verify-tool-pins.sh" "$REPO/.tools/missing.toml"
  assert_equal "$status" 2
}
