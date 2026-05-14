#!/usr/bin/env bats
load '../bats-helpers/fixtures'
load '../bats-helpers/assertions'

setup() { new_repo; install_gates_template; }
teardown() { cleanup_repo; }

@test "Verified: yes trailer added when all gates pass" {
  cd "$REPO"
  # Strip all real pre-commit gates so the run is clean — dispatcher still
  # writes gates-last-run (empty SKIPPED, empty FAILED) so trailer gate reads "yes".
  rm -rf .githooks/pre-commit.d/*
  echo "x" > a.txt
  git add a.txt
  git commit -m "feat: a"
  assert_verified_trailer "yes"
}

@test "Verified: no when --no-verify used" {
  cd "$REPO"
  echo "x" > a.txt
  git add a.txt
  # --no-verify skips pre-commit AND commit-msg. The trailer is never appended.
  # Absence of "Verified: yes" is itself the audit signal.
  git commit --no-verify -m "feat: a"
  run git log -1 --format=%B
  refute_output --partial "Verified: yes"
}

@test "Verified: partial when GATES_SKIP used" {
  cd "$REPO"
  rm -rf .githooks/pre-commit.d/*
  cat > .githooks/pre-commit.d/20-secrets <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  chmod +x .githooks/pre-commit.d/20-secrets
  echo "x" > a.txt
  git add a.txt
  GATES_SKIP="secrets" git commit -m "feat: a"
  assert_verified_trailer "partial"
}
