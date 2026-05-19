#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "resolve_tier returns warn for optional in standard" {
  cd "$REPO"
  result=$(bash -c '. .githooks/_profile.sh; resolve_tier complexity optional')
  [ "$result" = "warn" ]
}

@test "resolve_tier returns error for optional in regulated" {
  cd "$REPO"
  sed -i.bak 's/profile = "standard"/profile = "regulated"/' .gates.toml
  result=$(bash -c '. .githooks/_profile.sh; resolve_tier complexity optional')
  [ "$result" = "error" ]
}

@test "per-gate override beats profile" {
  cd "$REPO"
  cat >> .gates.toml <<'EOF'

[gates.complexity]
enforce = "off"
EOF
  result=$(bash -c '. .githooks/_profile.sh; resolve_tier complexity optional')
  [ "$result" = "off" ]
}

@test "resolve_tier returns off for optional in prototype profile" {
  cd "$REPO"
  sed -i.bak 's/profile = "standard"/profile = "prototype"/' .gates.toml
  result=$(bash -c '. .githooks/_profile.sh; resolve_tier complexity optional')
  [ "$result" = "off" ]
}
