#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

@test "setup_reference_repo creates a valid git repo with src/" {
  tmp=$(mktemp -d)
  setup_reference_repo "$tmp" "AddJwtBearer"
  [ -d "$tmp/src" ]
  [ -f "$tmp/Directory.Packages.props" ]
  ( cd "$tmp" && git log --oneline ) | grep -q init
  rm -rf "$tmp"
}

@test "assert_conventions_block_has matches detector id" {
  tmp=$(mktemp -d)
  cat > "$tmp/design.md" <<EOF
# x
<conventions reference-repo="r" reference-repo-commit="c" scanned-at="t" engine-version="0.1.0">
  <adopted detector="jwt-bearer" source="s" staged="x" packages=""/>
</conventions>
EOF
  run assert_conventions_block_has "$tmp/design.md" "jwt-bearer"
  [ "$status" -eq 0 ]
  rm -rf "$tmp"
}

@test "assert_staged_file_exists succeeds when file present" {
  tmp=$(mktemp -d)
  mkdir -p "$tmp/.scaffold/staged"
  echo body > "$tmp/.scaffold/staged/jwt-bearer.cs"
  run assert_staged_file_exists "$tmp" "jwt-bearer.cs"
  [ "$status" -eq 0 ]
  rm -rf "$tmp"
}
