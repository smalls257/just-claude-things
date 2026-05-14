# Test fixtures for bats gate tests.
# Provides helpers for creating and managing temporary test repos.

# Create a fresh git repo in a temp dir. Sets $REPO.
new_repo() {
  REPO="$(mktemp -d)"
  pushd "$REPO" >/dev/null
  git init -q -b main
  git config user.email "test@example.com"
  git config user.name "Test"
  popd >/dev/null
  export REPO
}

# Copy gate template tree into $REPO/.
install_gates_template() {
  local src="${BATS_TEST_DIRNAME}/../templates/common"
  cp -R "$src/githooks" "$REPO/.githooks"
  cp -R "$src/scripts" "$REPO/scripts"
  cp "$src/gitconfig-gates" "$REPO/.gitconfig.gates"
  cp "$src/gates.toml.example" "$REPO/.gates.toml"
  chmod +x "$REPO/.githooks/pre-commit" "$REPO/.githooks/pre-push" "$REPO/.githooks/commit-msg" 2>/dev/null || true
  chmod +x "$REPO"/.githooks/*.d/* 2>/dev/null || true
  chmod +x "$REPO"/scripts/*.sh 2>/dev/null || true
  git -C "$REPO" config --local include.path ../.gitconfig.gates
}

cleanup_repo() {
  if [ -n "${REPO:-}" ] && [ -d "$REPO" ]; then
    rm -rf "$REPO"
  fi
}
