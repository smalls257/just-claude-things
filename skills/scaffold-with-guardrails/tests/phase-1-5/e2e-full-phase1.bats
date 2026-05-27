#!/usr/bin/env bats
# Full e2e gate: deterministic Phase-1 emitter + convention-scan + graft
# + dotnet build. Catches scaffold.md drift (X7-class bugs) at unit time
# instead of via ad-hoc LLM-driven e2e dispatches.
#
# Complements e2e-scaffold-build.bats (which uses a hand-built fixture and
# skips real Phase-1). This test exercises the real dotnet new sequence.

SKILL_ROOT="$BATS_TEST_DIRNAME/../.."
FIXTURE_ROOT="$BATS_TEST_DIRNAME/../../test-fixtures/e2e-build"

setup() {
  command -v dotnet >/dev/null 2>&1 || skip "dotnet SDK not on PATH"
  command -v semgrep >/dev/null 2>&1 || skip "semgrep not on PATH"
  command -v python3 >/dev/null 2>&1 || skip "python3 not on PATH"

  # realpath resolves /var → /private/var on macOS. Without this, NuGet's
  # parallel restore sees the same project via both symlink paths and fails
  # with "project.assets.json already exists". bats sets BATS_TEST_TMPDIR
  # to /var/...; realpath gives us the canonical /private/var/... form.
  TARGET="$(realpath "$BATS_TEST_TMPDIR")/target"
  REF="$(realpath "$BATS_TEST_TMPDIR")/reference"

  # Reference repo — re-use the existing fixture so convention-scan has
  # detectors to offer (Serilog, CorrelationId).
  cp -R "$FIXTURE_ROOT/reference-repo" "$REF"
  git -C "$REF" init -q
  git -C "$REF" config user.email e2e@test
  git -C "$REF" config user.name e2e
  git -C "$REF" add -A
  git -C "$REF" commit -q -m "ref"
}

@test "full e2e: real Phase-1 emit + convention scan + graft + dotnet build = green" {
  # Step 1 — Phase-1: deterministic dotnet new + template copy + wiring.
  # SKIP_SEMGREP=1 suppresses the Directory.Build.targets semgrep gate during
  # the subsequent dotnet build so the test result is scoped to compilation,
  # not semgrep rule coverage (a separate concern).
  run python3 "$SKILL_ROOT/scripts/phase1_emit.py" \
    --target-root "$TARGET" \
    --app-name "MyApp"
  if [ "$status" -ne 0 ]; then
    echo "--- phase1_emit output ---"
    echo "$output"
  fi
  [ "$status" -eq 0 ]

  # Verify the slot markers that graft depends on are in the emitted Program.cs.
  grep -q "{{CONVENTION:logging}}" "$TARGET/src/MyApp.Api/Program.cs"
  grep -q "{{CONVENTION:middleware}}" "$TARGET/src/MyApp.Api/Program.cs"

  # Step 2 — init the target git repo (convention-scan needs a clean tree).
  git -C "$TARGET" init -q
  git -C "$TARGET" config user.email e2e@test
  git -C "$TARGET" config user.name e2e
  git -C "$TARGET" add -A
  git -C "$TARGET" commit -q -m "phase1"

  # Write minimal tech-design so convention-scan has a design to rewrite.
  mkdir -p "$TARGET/docs/tech-design"
  cat > "$TARGET/docs/tech-design/x.md" <<'EOF'
---
slug: x
---
# X
EOF
  git -C "$TARGET" add docs && git -C "$TARGET" commit -q -m "design"

  # Step 3 — convention scan. Two cards: Serilog (logging) + CorrelationId (middleware).
  run bash "$SKILL_ROOT/scripts/convention-scan.sh" \
    --reference-repo "$REF" \
    --target-repo "$TARGET" \
    --design "$TARGET/docs/tech-design/x.md" <<EOF
y
y
EOF
  if [ "$status" -ne 0 ]; then
    echo "--- convention-scan output ---"
    echo "$output"
  fi
  [ "$status" -eq 0 ]

  # Verify the staged snippets landed.
  [ -f "$TARGET/.scaffold/staged/serilog.cs" ]
  [ -f "$TARGET/.scaffold/staged/correlation-id.cs" ]

  # Step 4 — graft. SKIP_SEMGREP=1 prevents the semgrep BeforeTargets gate
  # from firing during dotnet format (called inside graft).
  run env SKIP_SEMGREP=1 python3 "$SKILL_ROOT/scripts/phase2_graft.py" \
    --design "$TARGET/docs/tech-design/x.md" \
    --target-program "$TARGET/src/MyApp.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged" \
    --target-root "$TARGET" \
    --app-name "MyApp" \
    --cpm "$TARGET/Directory.Packages.props"
  if [ "$status" -ne 0 ]; then
    echo "--- graft output ---"
    echo "$output"
  fi
  [ "$status" -eq 0 ]

  # Verify grafted wiring landed in Program.cs.
  grep -q "using MyApp.Api.Logging;" "$TARGET/src/MyApp.Api/Program.cs"
  grep -q "using MyApp.Api.Middleware;" "$TARGET/src/MyApp.Api/Program.cs"

  # Step 5 — restore after graft. Graft adds new PackageReferences (e.g.
  # Serilog) to csproj and their version pins to Directory.Packages.props.
  # This is the ONE restore for the tree; phase1_emit deliberately skips
  # restore to avoid collision. --use-lock-file generates packages.lock.json.
  run env SKIP_SEMGREP=1 dotnet restore "$TARGET/MyApp.sln" \
    --use-lock-file --nologo
  if [ "$status" -ne 0 ]; then
    echo "--- post-graft restore output ---"
    echo "$output"
  fi
  [ "$status" -eq 0 ]

  # Step 6 — dotnet build. This is the X-class catch: if Phase-1 emitted
  # wrong ProjectReferences (X7), wrong Program.cs markers (X2), bad XML
  # (X4), or mismatched csproj wiring, the build fails here with a clear
  # compiler error. --no-restore because we ran restore above. -maxcpucount:1
  # prevents the macOS /var↔/private/var symlink race where parallel MSBuild
  # workers write the same bin/*.deps.json file concurrently.
  run env SKIP_SEMGREP=1 dotnet build "$TARGET/MyApp.sln" \
    --no-restore --nologo -maxcpucount:1
  if [ "$status" -ne 0 ]; then
    echo "--- dotnet build FAILED ---"
    echo "$output"
    echo "--- Program.cs ---"
    cat "$TARGET/src/MyApp.Api/Program.cs"
    echo "--- Api csproj ---"
    cat "$TARGET/src/MyApp.Api/MyApp.Api.csproj"
    echo "--- Directory.Packages.props ---"
    cat "$TARGET/Directory.Packages.props"
    echo "--- DatabaseOptions.cs ---"
    cat "$TARGET/src/MyApp.Api/Configuration/DatabaseOptions.cs"
    echo "--- Worker.cs ---"
    cat "$TARGET/src/MyApp.Service/Worker.cs"
  fi
  [ "$status" -eq 0 ]
}
