#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/docs/tech-design"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  echo "untracked-noise" > "$TARGET/RANDOM.txt"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add docs/tech-design/svc.md && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "scan commit contains only design + staged dir, not unrelated noise" {
  run bash -c "printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  pushd "$TARGET" >/dev/null
  files=$(git show --name-only --pretty="" HEAD)
  echo "$files" | grep -q "docs/tech-design/svc.md"
  echo "$files" | grep -q ".scaffold/staged/"
  ! echo "$files" | grep -q "RANDOM.txt"
  popd >/dev/null
}
