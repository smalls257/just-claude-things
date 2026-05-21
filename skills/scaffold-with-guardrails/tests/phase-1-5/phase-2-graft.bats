#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  mkdir -p "$TARGET/docs/tech-design" "$TARGET/generated"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
  # Run scan first
  printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo "$REF" --target-repo "$TARGET" \
    --design "$TARGET/docs/tech-design/svc.md" --keywords ''
  # Seed a generated Program.cs with slot marker
  cat > "$TARGET/generated/Program.cs" <<'EOF'
var builder = WebApplication.CreateBuilder(args);
// {{CONVENTION:auth}}
var app = builder.Build();
app.Run();
EOF
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "phase-2 graft inserts adopted snippet at slot with SOURCE comment" {
  run python3 skills/scaffold-with-guardrails/scripts/phase2_graft.py \
    --design "$TARGET/docs/tech-design/svc.md" \
    --target-program "$TARGET/generated/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged"
  [ "$status" -eq 0 ]
  grep -q "// SOURCE: adopted:jwt-bearer" "$TARGET/generated/Program.cs"
  grep -q "AddJwtBearer" "$TARGET/generated/Program.cs"
  ! grep -q "{{CONVENTION:auth}}" "$TARGET/generated/Program.cs"
}
