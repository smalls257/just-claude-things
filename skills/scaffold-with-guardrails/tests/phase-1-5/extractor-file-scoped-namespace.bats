#!/usr/bin/env bats
# Bug #1: extractor failed when reference repo used C# file-scoped namespaces
# (namespace X; on its own line, body at root). Before the fix, _balance walked
# back from the hit line looking for an enclosing `{` that didn't exist and
# raised EXTRACT_FAILED, forcing devs to rewrite reference files to block-scoped
# form. After the fix, the extractor falls forward to the block the hit
# declares (enclosing-class) or walks outward until it finds a class-like
# header (enclosing-method-or-extension).

setup() {
  WORK=$(mktemp -d)
  SCRIPTS="/Users/jasonsmith/Code/just-claude-things/skills/scaffold-with-guardrails/scripts"
}
teardown() { rm -rf "$WORK"; }

@test "enclosing-class extracts file-scoped middleware class (hit on declaration line)" {
  cat > "$WORK/Corr.cs" <<'EOF'
namespace Reference.Api.Middleware;

public class CorrelationIdMiddleware
{
    private const string HeaderName = "X-Correlation-ID";
}
EOF
  run python3 -c "
import sys
sys.path.insert(0, '$SCRIPTS')
from convention_scan.extractor import extract
r = extract(__import__('pathlib').Path('$WORK/Corr.cs'), 3, 'enclosing-class')
print(r.text)
"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "public class CorrelationIdMiddleware"
  echo "$output" | grep -q "HeaderName"
  # MUST NOT include the namespace wrapper — the staged snippet is grafted
  # into Program.cs which has its own namespace context.
  ! echo "$output" | grep -q "namespace Reference.Api.Middleware"
}

@test "enclosing-method-or-extension extracts file-scoped static class wrapper" {
  cat > "$WORK/Ser.cs" <<'EOF'
using Serilog;

namespace Reference.Api.Logging;

public static class SerilogConfig
{
    public static void Configure(WebApplicationBuilder builder)
    {
        builder.Host.UseSerilog();
    }
}
EOF
  run python3 -c "
import sys
sys.path.insert(0, '$SCRIPTS')
from convention_scan.extractor import extract
r = extract(__import__('pathlib').Path('$WORK/Ser.cs'), 9, 'enclosing-method-or-extension')
print(r.text)
"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "public static class SerilogConfig"
  echo "$output" | grep -q "UseSerilog"
}
