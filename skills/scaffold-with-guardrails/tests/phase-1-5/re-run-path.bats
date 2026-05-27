#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/docs/tech-design"
  cat > "$TARGET/docs/tech-design/svc.md" <<EOF
# svc
<module name="core"/>

<conventions reference-repo="r" reference-repo-commit="c" scanned-at="t" engine-version="0.1.0">
  <adopted detector="jwt-bearer" source="old" staged="staged/jwt-bearer.cs" packages=""/>
</conventions>
EOF
  mkdir -p "$TARGET/.scaffold/staged"
  echo "old-snippet" > "$TARGET/.scaffold/staged/jwt-bearer.cs"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "re-run replaces conventions block atomically + updates staged snippet" {
  run bash -c "printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  ! grep -q 'source="old"' "$TARGET/docs/tech-design/svc.md"
  grep -q 'AddJwtBearer' "$TARGET/.scaffold/staged/jwt-bearer.cs"
}
