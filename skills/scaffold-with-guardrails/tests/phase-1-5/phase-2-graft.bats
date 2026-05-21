#!/usr/bin/env bats
load ../bats-helpers/convention-fixtures

setup() {
  TARGET=$(mktemp -d)
  REF=$(mktemp -d)
  setup_reference_repo "$REF" "AddJwtBearer"
  # Bug #6 forced the new layout: graft writes host files under
  # src/<App>.Api/<LayerDir>/<Class>.cs, then replaces the slot marker with a
  # single call line. The test target needs that layout under target root so
  # the host file lands where the App project expects.
  mkdir -p "$TARGET/docs/tech-design" "$TARGET/src/Svc.Api"
  printf '# svc\n<module name="core"/>\n' > "$TARGET/docs/tech-design/svc.md"
  ( cd "$TARGET" && git init -q && git -c user.email=t@t -c user.name=t add -A && git -c user.email=t@t -c user.name=t commit -q -m init )
  # Run scan first
  printf 'y\ny\ny\ny\ny\n' | bash skills/scaffold-with-guardrails/scripts/convention-scan.sh \
    --reference-repo "$REF" --target-repo "$TARGET" \
    --design "$TARGET/docs/tech-design/svc.md" --keywords ''
  # Seed a generated Program.cs with slot marker
  cat > "$TARGET/src/Svc.Api/Program.cs" <<'EOF'
var builder = WebApplication.CreateBuilder(args);
// {{CONVENTION:auth}}
var app = builder.Build();
app.Run();
EOF
}

teardown() { rm -rf "$TARGET" "$REF"; }

@test "phase-2 graft emits call line at slot and writes class to host file" {
  run python3 skills/scaffold-with-guardrails/scripts/phase2_graft.py \
    --design "$TARGET/docs/tech-design/svc.md" \
    --target-program "$TARGET/src/Svc.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged"
  [ "$status" -eq 0 ]
  # 1. The slot was replaced. Verify the call line landed and the slot is gone.
  grep -q "// SOURCE: adopted:jwt-bearer" "$TARGET/src/Svc.Api/Program.cs"
  ! grep -q "{{CONVENTION:auth}}" "$TARGET/src/Svc.Api/Program.cs"
  # 2. The class block must NOT be inlined into Program.cs (top-level
  # statements cannot host nested class declarations).
  ! grep -q "public static class AuthExt" "$TARGET/src/Svc.Api/Program.cs"
  ! grep -q "AddJwtBearer" "$TARGET/src/Svc.Api/Program.cs"
  # 3. AuthExt is an extension on IServiceCollection — call site is
  # builder.Services.AddAuth();
  grep -q "builder.Services.AddAuth();" "$TARGET/src/Svc.Api/Program.cs"
  # 4. The class was written to a host file under the Auth/ subdir.
  [ -f "$TARGET/src/Svc.Api/Auth/AuthExt.cs" ]
  grep -q "public static class AuthExt" "$TARGET/src/Svc.Api/Auth/AuthExt.cs"
  grep -q "AddJwtBearer" "$TARGET/src/Svc.Api/Auth/AuthExt.cs"
  grep -q "namespace Svc.Api.Auth;" "$TARGET/src/Svc.Api/Auth/AuthExt.cs"
}
