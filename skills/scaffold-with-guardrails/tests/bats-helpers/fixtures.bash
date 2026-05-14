# Test fixtures for bats gate tests.
# Provides helpers for creating and managing temporary test repos.

# shellcheck disable=SC2154
_BATS_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create a fresh git repo in a temp dir. Sets $REPO.
new_repo() {
  REPO="$(mktemp -d)"
  git init -q -b main "$REPO"
  git -C "$REPO" config user.email "test@example.com"
  git -C "$REPO" config user.name "Test"
  export REPO
}

# Copy gate template tree into $REPO/.
install_gates_template() {
  local src="${_BATS_HELPERS_DIR}/../../templates/common"
  cp -R "$src/githooks" "$REPO/.githooks" || { echo "failed to copy githooks" >&2; return 1; }
  cp -R "$src/scripts" "$REPO/scripts" || { echo "failed to copy scripts" >&2; return 1; }
  cp "$src/gitconfig-gates" "$REPO/.gitconfig.gates" || { echo "failed to copy gitconfig-gates" >&2; return 1; }
  cp "$src/gates.toml.example" "$REPO/.gates.toml" || { echo "failed to copy gates.toml.example" >&2; return 1; }
  chmod +x "$REPO/.githooks/pre-commit" "$REPO/.githooks/pre-push" "$REPO/.githooks/commit-msg" 2>/dev/null || true
  chmod +x "$REPO"/.githooks/*.d/* 2>/dev/null || true
  chmod +x "$REPO"/scripts/*.sh 2>/dev/null || true
  mkdir -p "$REPO/.tools" || { echo "failed to mkdir .tools" >&2; return 1; }
  cp "$src/tools/manifest.toml.template" "$REPO/.tools/manifest.toml" || { echo "failed to copy manifest.toml" >&2; return 1; }
  cp "$src/tools/gitignore-template" "$REPO/.tools/.gitignore" || { echo "failed to copy tools gitignore" >&2; return 1; }
  git -C "$REPO" config --local include.path ../.gitconfig.gates
}

cleanup_repo() {
  if [ -n "${REPO:-}" ] && [ -d "$REPO" ]; then
    rm -rf "$REPO"
  fi
}

# Mirror the gate template tree from $REPO into a worktree directory.
# Usage: mirror_gates_into_worktree "$WT"
mirror_gates_into_worktree() {
  local wt="$1"
  cp -R "$REPO/.githooks" "$wt/.githooks" || { echo "failed to mirror .githooks" >&2; return 1; }
  cp -R "$REPO/scripts"   "$wt/scripts"   || { echo "failed to mirror scripts" >&2; return 1; }
  cp "$REPO/.gitconfig.gates" "$wt/.gitconfig.gates" || { echo "failed to mirror .gitconfig.gates" >&2; return 1; }
  cp "$REPO/.gates.toml" "$wt/.gates.toml" || { echo "failed to mirror .gates.toml" >&2; return 1; }
  chmod +x "$wt/scripts"/*.sh 2>/dev/null || true
  chmod +x "$wt/.githooks"/{pre-commit,pre-push,commit-msg} 2>/dev/null || true
}
