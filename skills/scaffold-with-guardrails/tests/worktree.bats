#!/usr/bin/env bats
load 'bats-helpers/fixtures'
load 'bats-helpers/assertions'

setup() {
  new_repo
  install_gates_template
  # Need at least one commit to add a worktree.
  cd "$REPO"
  echo "init" > README.md
  git -C "$REPO" add README.md
  git -c core.hooksPath=/dev/null -C "$REPO" commit -m "init"
}

teardown() {
  # Best-effort: remove worktree before nuking the repo
  if [ -n "${WT:-}" ] && [ -d "$WT" ]; then
    git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || true
    rm -rf "$WT"
  fi
  cleanup_repo
}

@test "include.path applies to worktree" {
  WT="$(mktemp -d)"; rm -rf "$WT"  # mktemp leaves a dir; worktree add wants it absent
  git -C "$REPO" worktree add "$WT" -b feature/test
  run git -C "$WT" config --get include.path
  assert_output "../.gitconfig.gates"
  run git -C "$WT" config --get core.hooksPath
  assert_output ".githooks"
}

@test "bootstrap in worktree writes config to common-dir, not worktree gitdir" {
  WT="$(mktemp -d)"; rm -rf "$WT"
  git -C "$REPO" worktree add "$WT" -b feature/test
  mirror_gates_into_worktree "$WT"
  run "$WT/scripts/bootstrap.sh" --offline
  assert_success
  run git -C "$WT" config --get include.path
  assert_output "../.gitconfig.gates"
  # Bootstrap wrote --local config, which in a worktree lands on the common-dir config.
  common_dir="$(git -C "$WT" rev-parse --git-common-dir)"
  run grep -F "../.gitconfig.gates" "$common_dir/config"
  assert_success
  # The worktree's own gitdir does NOT have its own config file (default git behavior)
  wt_gitdir="$(git -C "$WT" rev-parse --git-dir)"
  [ ! -f "$wt_gitdir/config" ] || ! grep -q "include.path" "$wt_gitdir/config" || \
    { echo "expected no worktree-local config OR no include.path in it; found one in $wt_gitdir/config" >&2; false; }
}

@test "dispatcher in worktree writes perf log to common-dir" {
  WT="$(mktemp -d)"; rm -rf "$WT"
  git -C "$REPO" worktree add "$WT" -b feature/test
  mirror_gates_into_worktree "$WT"
  git -C "$WT" config --local include.path ../.gitconfig.gates
  # Add a noop gate so dispatcher has something to run
  mkdir -p "$WT/.githooks/pre-commit.d"
  cat > "$WT/.githooks/pre-commit.d/05-noop" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  chmod +x "$WT/.githooks/pre-commit.d/05-noop"
  echo "y" > "$WT/file.txt"
  git -C "$WT" add file.txt
  run git -C "$WT" commit -m "worktree commit"
  assert_success
  # Perf log should land in the common-dir (the original repo's .git), not the worktree gitdir
  common_dir="$(git -C "$WT" rev-parse --git-common-dir)"
  run cat "$common_dir/gates-perf.log"
  assert_output --partial "pre-commit 05-noop"
}
