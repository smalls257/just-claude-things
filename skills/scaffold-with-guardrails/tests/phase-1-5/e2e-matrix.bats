#!/usr/bin/env bats
# Fixture-matrix e2e: runs the full pipeline against each reference-repo
# shape under test-fixtures/e2e-build/. Catches detector/graft regressions
# at unit-suite time across multiple convention layers.
#
# Slow — each fixture costs ~30-60s (dotnet new + restore + build).
#
# Fixture → detector mapping:
#   reference-repo              → serilog (logging) + correlation-id (middleware)
#   reference-repo-mediatr      → validation-pipeline (middleware/FluentValidation)
#   reference-repo-problem-details → exception-handler (middleware)
#   reference-repo-jwt          → jwt-bearer (auth)

SKILL_ROOT="$BATS_TEST_DIRNAME/../.."
FIXTURE_ROOT="$BATS_TEST_DIRNAME/../../test-fixtures/e2e-build"

setup_common() {
  command -v dotnet >/dev/null 2>&1 || skip "dotnet SDK not on PATH"
  command -v semgrep >/dev/null 2>&1 || skip "semgrep not on PATH"
  command -v python3 >/dev/null 2>&1 || skip "python3 not on PATH"

  # realpath resolves /var -> /private/var on macOS. Without this, NuGet's
  # parallel restore sees the same project via both symlink paths and fails
  # with "project.assets.json already exists".
  TMPDIR_REAL="$(realpath "$BATS_TEST_TMPDIR")"
  TARGET="$TMPDIR_REAL/target"
  REF="$TMPDIR_REAL/reference"
}

# Run the full pipeline against $REF + $TARGET. Caller seeds $REF and runs
# phase1_emit before calling this. The helper asserts each step exits 0.
run_pipeline() {
  local app_name="$1"
  local adopt_answers="$2"  # newline-separated y/n string

  # Phase-1 emit
  run python3 "$SKILL_ROOT/scripts/phase1_emit.py" \
    --target-root "$TARGET" --app-name "$app_name"
  [ "$status" -eq 0 ] || { echo "phase1_emit FAILED:"; echo "$output"; return 1; }

  # Target git init
  git -C "$TARGET" init -q
  git -C "$TARGET" config user.email e2e@test
  git -C "$TARGET" config user.name e2e
  git -C "$TARGET" add -A
  git -C "$TARGET" commit -q -m "phase1"

  # Tech-design stub
  mkdir -p "$TARGET/docs/tech-design"
  cat > "$TARGET/docs/tech-design/x.md" <<'EOF'
---
slug: x
---
# X
EOF
  git -C "$TARGET" add docs && git -C "$TARGET" commit -q -m "design"

  # Scan
  run bash "$SKILL_ROOT/scripts/convention-scan.sh" \
    --reference-repo "$REF" \
    --target-repo "$TARGET" \
    --design "$TARGET/docs/tech-design/x.md" <<< "$adopt_answers"
  [ "$status" -eq 0 ] || { echo "scan FAILED:"; echo "$output"; return 1; }

  # Graft
  run env SKIP_SEMGREP=1 python3 "$SKILL_ROOT/scripts/phase2_graft.py" \
    --design "$TARGET/docs/tech-design/x.md" \
    --target-program "$TARGET/src/$app_name.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged" \
    --target-root "$TARGET" \
    --app-name "$app_name" \
    --cpm "$TARGET/Directory.Packages.props"
  [ "$status" -eq 0 ] || { echo "graft FAILED:"; echo "$output"; return 1; }

  # Restore
  run env SKIP_SEMGREP=1 dotnet restore "$TARGET/$app_name.sln" \
    --use-lock-file --nologo
  [ "$status" -eq 0 ] || { echo "restore FAILED:"; echo "$output"; return 1; }

  # Build
  run env SKIP_SEMGREP=1 dotnet build "$TARGET/$app_name.sln" \
    --no-restore --nologo -maxcpucount:1
  [ "$status" -eq 0 ] || { echo "build FAILED:"; echo "$output"; return 1; }
}

@test "matrix: serilog + correlation-id reference repo builds" {
  setup_common
  cp -R "$FIXTURE_ROOT/reference-repo" "$REF"
  git -C "$REF" init -q
  git -C "$REF" config user.email e2e@test
  git -C "$REF" config user.name e2e
  git -C "$REF" add -A && git -C "$REF" commit -q -m "ref"

  # Two adoption prompts: serilog (logging) + correlation-id (middleware).
  run_pipeline "MyApp" "$(printf 'y\ny\n')"
}

@test "matrix: validation-pipeline (FluentValidation) reference repo builds" {
  setup_common
  cp -R "$FIXTURE_ROOT/reference-repo-mediatr" "$REF"
  git -C "$REF" init -q
  git -C "$REF" config user.email e2e@test
  git -C "$REF" config user.name e2e
  git -C "$REF" add -A && git -C "$REF" commit -q -m "ref"

  # One adoption prompt: validation-pipeline card.
  run_pipeline "ValidationApp" "$(printf 'y\n')"
}

@test "matrix: exception-handler (problem-details) reference repo builds" {
  setup_common
  cp -R "$FIXTURE_ROOT/reference-repo-problem-details" "$REF"
  git -C "$REF" init -q
  git -C "$REF" config user.email e2e@test
  git -C "$REF" config user.name e2e
  git -C "$REF" add -A && git -C "$REF" commit -q -m "ref"

  # One adoption prompt: exception-handler card (problem-details is a
  # lower-priority conflict loser and is suppressed).
  run_pipeline "ExceptionApp" "$(printf 'y\n')"
}

@test "matrix: jwt-bearer reference repo builds" {
  setup_common
  cp -R "$FIXTURE_ROOT/reference-repo-jwt" "$REF"
  git -C "$REF" init -q
  git -C "$REF" config user.email e2e@test
  git -C "$REF" config user.name e2e
  git -C "$REF" add -A && git -C "$REF" commit -q -m "ref"

  # One adoption prompt: jwt-bearer card.
  run_pipeline "JwtApp" "$(printf 'y\n')"
}
