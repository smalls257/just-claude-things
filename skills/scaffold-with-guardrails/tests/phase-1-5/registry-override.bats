#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/.scaffold/detectors" "$TARGET/docs/tech-design"
  cat > "$TARGET/.scaffold/detectors/jwt-bearer.yaml" <<'EOF'
id: jwt-bearer
display: JWT (project-customised)
layer: auth
priority: 99
files: ["src/**/*.cs"]
signal:
  cs: ["AddJwtBearer"]
extract: enclosing-method-or-extension
notes: project-override-active
EOF
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "project override replaces skill default by id" {
  run bash -c "printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo '$REF' --target-repo '$TARGET' \
    --design '$TARGET/docs/tech-design/svc.md' --keywords ''"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "project-customised"
}
