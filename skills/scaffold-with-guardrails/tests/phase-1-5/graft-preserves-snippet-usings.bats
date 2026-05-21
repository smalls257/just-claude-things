#!/usr/bin/env bats
# Bug A end-to-end: graft against a snippet with snippet usings + a known
# third-party root must produce a host file with merged usings, a NuGet
# TODO breadcrumb, and a Program.cs with the matching reverse-using line.

load '../bats-helpers/fixtures'

setup() {
  new_repo
  TARGET="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$TARGET/src/MyApp.Api" "$TARGET/.scaffold/staged" "$TARGET/docs/tech-design"

  cat > "$TARGET/src/MyApp.Api/Program.cs" <<'EOF'
using System;
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
// {{CONVENTION:logging}}
var app = builder.Build();
app.Run();
EOF

  cat > "$TARGET/.scaffold/staged/serilog.cs" <<'EOF'
using Serilog;

public static class SerilogConfig
{
    public static void Configure(WebApplicationBuilder builder)
    {
        Log.Logger = new LoggerConfiguration().CreateLogger();
        builder.Host.UseSerilog();
    }
}
EOF

  cat > "$TARGET/docs/tech-design/x.md" <<'EOF'
---
slug: x
---
<conventions reference-repo="r" reference-repo-commit="c" scanned-at="2026-05-20T00:00:00Z" engine-version="0.1.0">
  <adopted detector="serilog" source="src/Logging/SerilogConfig.cs:L1-L20" staged="staged/serilog.cs" packages=""/>
</conventions>
EOF
}

teardown() { cleanup_repo; }

@test "graft writes host file with snippet usings + NuGet TODO" {
  run python3 "$BATS_TEST_DIRNAME/../../scripts/phase2_graft.py" \
    --design "$TARGET/docs/tech-design/x.md" \
    --target-program "$TARGET/src/MyApp.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged" \
    --target-root "$TARGET" \
    --app-name "MyApp"

  [ "$status" -eq 0 ]
  [ -f "$TARGET/src/MyApp.Api/Logging/SerilogConfig.cs" ]
  grep -q "using Serilog;" "$TARGET/src/MyApp.Api/Logging/SerilogConfig.cs"
  grep -q "// TODO NUGET: Serilog" "$TARGET/src/MyApp.Api/Logging/SerilogConfig.cs"
  grep -q "using MyApp.Api.Logging;" "$TARGET/src/MyApp.Api/Program.cs"
}

@test "graft is idempotent — re-run does not duplicate Program.cs using" {
  python3 "$BATS_TEST_DIRNAME/../../scripts/phase2_graft.py" \
    --design "$TARGET/docs/tech-design/x.md" \
    --target-program "$TARGET/src/MyApp.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged" \
    --target-root "$TARGET" \
    --app-name "MyApp"
  # Second run — should be a no-op for the Program.cs using.
  run python3 "$BATS_TEST_DIRNAME/../../scripts/phase2_graft.py" \
    --design "$TARGET/docs/tech-design/x.md" \
    --target-program "$TARGET/src/MyApp.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged" \
    --target-root "$TARGET" \
    --app-name "MyApp"
  # NOTE: the slot marker no longer exists after first graft, so this
  # second run is expected to print NO_SLOT and exit non-zero. The
  # IDEMPOTENCY assertion is that Program.cs's using-count is still 1.
  count=$(grep -c "using MyApp.Api.Logging;" "$TARGET/src/MyApp.Api/Program.cs")
  [ "$count" -eq 1 ]
}
