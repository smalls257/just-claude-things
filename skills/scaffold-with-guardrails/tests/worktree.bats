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
  # Mirror gate tree into worktree
  cp -R "$REPO/.githooks" "$WT/.githooks"
  cp -R "$REPO/scripts" "$WT/scripts"
  cp "$REPO/.gitconfig.gates" "$WT/.gitconfig.gates"
  cp "$REPO/.gates.toml" "$WT/.gates.toml"
  chmod +x "$WT/scripts"/*.sh "$WT/.githooks"/{pre-commit,pre-push,commit-msg}
  run "$WT/scripts/bootstrap.sh" --offline
  assert_success
  # include.path now set on the worktree gitdir
  run git -C "$WT" config --get include.path
  assert_output "../.gitconfig.gates"
}

@test "dispatcher in worktree writes perf log to common-dir" {
  WT="$(mktemp -d)"; rm -rf "$WT"
  git -C "$REPO" worktree add "$WT" -b feature/test
  cp -R "$REPO/.githooks" "$WT/.githooks"
  cp -R "$REPO/scripts" "$WT/scripts"
  cp "$REPO/.gitconfig.gates" "$WT/.gitconfig.gates"
  cp "$REPO/.gates.toml" "$WT/.gates.toml"
  git -C "$WT" config --local include.path ../.gitconfig.gates
  chmod +x "$WT/.githooks"/{pre-commit,pre-push,commit-msg}
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
