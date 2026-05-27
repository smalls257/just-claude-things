#!/usr/bin/env bats
# E2E build gate: runs the full convention-scan + phase2_graft + dotnet build
# chain against in-repo fixtures. Asserts exit 0. This is the gate that
# catches "X-class" bugs (X1 csproj versions, X2 marker positions, X4 XML
# formatting, etc.) at unit-suite time instead of via ad-hoc e2e dispatch.

load '../bats-helpers/fixtures'

FIXTURE_ROOT="$BATS_TEST_DIRNAME/../../test-fixtures/e2e-build"
SKILL_ROOT="$BATS_TEST_DIRNAME/../.."

setup() {
  # Skip if dotnet not on PATH — this test needs a real .NET SDK.
  command -v dotnet >/dev/null 2>&1 || skip "dotnet SDK not on PATH"

  TARGET="$BATS_TEST_TMPDIR/target"
  REF="$BATS_TEST_TMPDIR/reference"
  cp -R "$FIXTURE_ROOT/target-template" "$TARGET"
  cp -R "$FIXTURE_ROOT/reference-repo" "$REF"

  # Reference repo must have a clean git tree for the convention-scan
  # dirty-check.
  git -C "$REF" init -q
  git -C "$REF" config user.email e2e@test
  git -C "$REF" config user.name e2e
  git -C "$REF" add -A
  git -C "$REF" commit -q -m "ref"

  # Target also needs git for the scan's autocommit step.
  git -C "$TARGET" init -q
  git -C "$TARGET" config user.email e2e@test
  git -C "$TARGET" config user.name e2e
  git -C "$TARGET" add -A
  git -C "$TARGET" commit -q -m "target"
}

teardown() {
  :
}

@test "e2e: convention scan + graft + dotnet build = green" {
  # Step 1: run convention scan. Two cards are adopted: Serilog (logging)
  # and CorrelationId middleware — the middleware uses a braceless `if`
  # which is the X6 trigger. Two `y` answers, one per card.
  run bash "$SKILL_ROOT/scripts/convention-scan.sh" \
    --reference-repo "$REF" \
    --target-repo "$TARGET" \
    --design "$TARGET/docs/tech-design/x.md" <<EOF
y
y
EOF
  [ "$status" -eq 0 ]

  # Sanity check: conventions block was rewritten with both adopted decisions.
  grep -q 'detector="serilog"' "$TARGET/docs/tech-design/x.md"
  [ -f "$TARGET/.scaffold/staged/serilog.cs" ]
  grep -q "using Serilog;" "$TARGET/.scaffold/staged/serilog.cs"
  grep -q 'detector="correlation-id"' "$TARGET/docs/tech-design/x.md"
  [ -f "$TARGET/.scaffold/staged/correlation-id.cs" ]

  # Step 2: graft (dotnet format runs automatically after graft to fix X6).
  run python3 "$SKILL_ROOT/scripts/phase2_graft.py" \
    --design "$TARGET/docs/tech-design/x.md" \
    --target-program "$TARGET/src/MyApp.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged" \
    --target-root "$TARGET" \
    --app-name "MyApp" \
    --cpm "$TARGET/Directory.Packages.props"
  [ "$status" -eq 0 ]

  # Sanity check: Serilog host file and Program.cs wiring.
  [ -f "$TARGET/src/MyApp.Api/Logging/SerilogConfig.cs" ]
  grep -q "using Serilog;" "$TARGET/src/MyApp.Api/Logging/SerilogConfig.cs"
  grep -q "using MyApp.Api.Logging;" "$TARGET/src/MyApp.Api/Program.cs"

  # Sanity check: CorrelationId middleware host file and Program.cs wiring.
  # X6 gate: if dotnet format failed to add braces, IDE0011 will fire below.
  [ -f "$TARGET/src/MyApp.Api/Middleware/CorrelationIdMiddleware.cs" ]
  grep -q "using MyApp.Api.Middleware;" "$TARGET/src/MyApp.Api/Program.cs"
  grep -q "app.UseMiddleware<CorrelationIdMiddleware>" "$TARGET/src/MyApp.Api/Program.cs"

  # Step 3: dotnet build the target. This is the X-class catch — if any
  # generated file is malformed (wrong XML, wrong namespace, missing
  # using, bad marker position, or braceless `if` under TWAE), build fails here.
  run env -u DOTNET_CLI_TELEMETRY_OPTOUT dotnet build "$TARGET/MyApp.sln" --nologo
  if [ "$status" -ne 0 ]; then
    echo "----------------------------------------"
    echo "dotnet build FAILED — full output:"
    echo "$output"
    echo "----------------------------------------"
    echo "Generated Program.cs:"
    cat "$TARGET/src/MyApp.Api/Program.cs"
    echo "----------------------------------------"
    echo "Generated Directory.Packages.props:"
    cat "$TARGET/Directory.Packages.props"
    echo "----------------------------------------"
    echo "Generated Serilog host file:"
    cat "$TARGET/src/MyApp.Api/Logging/SerilogConfig.cs"
    echo "----------------------------------------"
    echo "Generated CorrelationId host file (X6 trigger):"
    cat "$TARGET/src/MyApp.Api/Middleware/CorrelationIdMiddleware.cs"
  fi
  [ "$status" -eq 0 ]
}
