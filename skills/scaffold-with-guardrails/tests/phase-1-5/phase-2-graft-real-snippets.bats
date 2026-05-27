#!/usr/bin/env bats
# Bug #6: convention-scan stages full `public static class X { ... }` blocks
# (or namespace-wrapped middleware classes). Inlining those at the slot in a
# top-level-statements Program.cs is invalid C# (nested class declarations
# cannot appear between statements).
#
# The fix moves each staged class to src/<App>.Api/<LayerDir>/<Class>.cs and
# replaces the marker with a single call line. This test pins the call-shape
# inference against the three actual staged snippets harvested from the
# sim-library end-to-end run.

setup() {
  TARGET=$(mktemp -d)
  mkdir -p "$TARGET/src/Library.Api" "$TARGET/.scaffold/staged" "$TARGET/docs/tech-design"

  # Three staged snippets — one per call-shape branch. Layout matches what
  # convention-scan stages today (indented bodies, namespace-wrapped middleware).
  cat > "$TARGET/.scaffold/staged/serilog.cs" <<'EOF'
    public static class SerilogConfig
    {
        public static void Configure(WebApplicationBuilder builder)
        {
            builder.Host.UseSerilog();
        }
    }
EOF
  cat > "$TARGET/.scaffold/staged/correlation-id.cs" <<'EOF'
namespace Reference.Api.Middleware
{
    public class CorrelationIdMiddleware
    {
        private readonly RequestDelegate _next;

        public CorrelationIdMiddleware(RequestDelegate next)
        {
            _next = next;
        }

        public async Task InvokeAsync(HttpContext context)
        {
            await _next(context);
        }
    }
}
EOF
  cat > "$TARGET/.scaffold/staged/repository-pattern.cs" <<'EOF'
    public static class Bootstrap
    {
        public static void RegisterRepositories(IServiceCollection services)
        {
            services.AddScoped<ITitleRepository, TitleRepository>();
        }
    }
EOF

  # Design with all three adopted.
  cat > "$TARGET/docs/tech-design/lib.md" <<'EOF'
# Library

<conventions reference-repo="ref" reference-repo-commit="abc" scanned-at="2026-05-20T00:00:00Z" engine-version="1">
  <adopted detector="serilog" source="src/Logging/SerilogConfig.cs:L1-L7" staged="serilog.cs" packages="" />
  <adopted detector="correlation-id" source="src/Middleware/CorrelationIdMiddleware.cs:L1-L20" staged="correlation-id.cs" packages="" />
  <adopted detector="repository-pattern" source="src/Data/Bootstrap.cs:L1-L7" staged="repository-pattern.cs" packages="" />
</conventions>
EOF

  cat > "$TARGET/src/Library.Api/Program.cs" <<'EOF'
var builder = WebApplication.CreateBuilder(args);

// {{CONVENTION:logging}}
// {{CONVENTION:data}}

var app = builder.Build();

// {{CONVENTION:middleware}}

app.Run();
EOF
}

teardown() { rm -rf "$TARGET"; }

@test "graft writes per-layer host files and emits the right call line for each shape" {
  run python3 skills/scaffold-with-guardrails/scripts/phase2_graft.py \
    --design "$TARGET/docs/tech-design/lib.md" \
    --target-program "$TARGET/src/Library.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged"
  [ "$status" -eq 0 ]

  # 1. Serilog: static method on WebApplicationBuilder -> SerilogConfig.Configure(builder);
  grep -q "SerilogConfig.Configure(builder);" "$TARGET/src/Library.Api/Program.cs"
  [ -f "$TARGET/src/Library.Api/Logging/SerilogConfig.cs" ]
  grep -q "namespace Library.Api.Logging;" "$TARGET/src/Library.Api/Logging/SerilogConfig.cs"

  # 2. Middleware class: app.UseMiddleware<T>();
  grep -q "app.UseMiddleware<CorrelationIdMiddleware>();" "$TARGET/src/Library.Api/Program.cs"
  [ -f "$TARGET/src/Library.Api/Middleware/CorrelationIdMiddleware.cs" ]

  # 3. Repository registration: static method on IServiceCollection -> Bootstrap.RegisterRepositories(builder.Services);
  grep -q "Bootstrap.RegisterRepositories(builder.Services);" "$TARGET/src/Library.Api/Program.cs"
  [ -f "$TARGET/src/Library.Api/Data/Bootstrap.cs" ]

  # 4. The class declarations themselves are NOT in Program.cs (the bug).
  ! grep -q "public static class SerilogConfig" "$TARGET/src/Library.Api/Program.cs"
  ! grep -q "public class CorrelationIdMiddleware" "$TARGET/src/Library.Api/Program.cs"
  ! grep -q "public static class Bootstrap" "$TARGET/src/Library.Api/Program.cs"

  # 5. Every adopted layer left a SOURCE attribution line.
  grep -q "// SOURCE: adopted:serilog" "$TARGET/src/Library.Api/Program.cs"
  grep -q "// SOURCE: adopted:correlation-id" "$TARGET/src/Library.Api/Program.cs"
  grep -q "// SOURCE: adopted:repository-pattern" "$TARGET/src/Library.Api/Program.cs"
}

@test "graft leaves TODO comment when entry shape cannot be inferred" {
  # A snippet with no static methods and no InvokeAsync — graft cannot guess
  # the call site. Should not crash; should leave a TODO breadcrumb so the
  # dev can wire it manually.
  cat > "$TARGET/.scaffold/staged/serilog.cs" <<'EOF'
    public class OpaqueThing
    {
        public OpaqueThing() { }
    }
EOF
  run python3 skills/scaffold-with-guardrails/scripts/phase2_graft.py \
    --design "$TARGET/docs/tech-design/lib.md" \
    --target-program "$TARGET/src/Library.Api/Program.cs" \
    --staged-root "$TARGET/.scaffold/staged"
  [ "$status" -eq 0 ]
  grep -q "TODO: wire OpaqueThing" "$TARGET/src/Library.Api/Program.cs"
}
