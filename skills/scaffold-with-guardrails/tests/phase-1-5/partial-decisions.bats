#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/.scaffold/staged" "$TARGET/docs/tech-design"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "partial decisions file restored on resume" {
  cat > "$TARGET/.scaffold/staged/.partial-decisions.json" <<EOF
{
  "jwt-bearer": "y"
}
EOF
  CARDS=$(mktemp)
  echo "CARD: jwt-bearer" > "$CARDS"
  OUT=$(mktemp)
  run bash skills/scaffold-with-guardrails/scripts/convention_scan_prompter.sh \
    --cards "$CARDS" --out "$OUT" \
    --partial "$TARGET/.scaffold/staged/.partial-decisions.json" < /dev/null
  [ "$status" -eq 0 ]
  grep -q '"jwt-bearer": "y"' "$OUT"
}
