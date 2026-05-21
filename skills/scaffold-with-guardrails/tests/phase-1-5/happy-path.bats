#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures
load ../bats-helpers/assertions

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/docs/tech-design"
  cat > "$TARGET/docs/tech-design/svc.md" <<EOF
# svc
<module name="core"/>
EOF
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() {
  rm -rf "$TARGET" "$REF"
}

@test "happy path produces conventions block + staged file + commit" {
  run bash -c "printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  assert_conventions_block_has "$TARGET/docs/tech-design/svc.md" "jwt-bearer"
  assert_staged_file_exists "$TARGET" "jwt-bearer.cs"
  ( cd "$TARGET" && git log --oneline | grep -q "convention scan" )
}
